"""
Excel to Supabase Push Script for Donnerstagsspiel

Validates, transforms, and uploads song data to Supabase cloud database.

Usage:
    python push_to_supabase.py                    # Full push
    python push_to_supabase.py --validate-only    # Only validate Excel
    python push_to_supabase.py --dry-run          # Show what would be pushed
    python push_to_supabase.py --migrate-likes    # Also migrate likes.json
    python push_to_supabase.py --help             # Show help

Environment Variables Required:
    SUPABASE_URL         - Your Supabase project URL
    SUPABASE_SERVICE_KEY - Your Supabase service role key (for writes)

Or create a .env file with these values.
"""

import os
import sys
import json
import argparse
import unicodedata
import re
from pathlib import Path
from datetime import datetime

import pandas as pd

# Load .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv is optional

# Import Supabase client
try:
    from supabase import create_client, Client
except ImportError:
    print("ERROR: supabase package not installed.")
    print("Run: pip install supabase")
    sys.exit(1)


# =============================================================================
# CONFIGURATION
# =============================================================================

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

DATA_DIR = Path("data")
LIKES_FILE = DATA_DIR / "likes.json"


# =============================================================================
# NORMALIZATION (same as main.py)
# =============================================================================

def normalize_song_name(song: str) -> str:
    """
    Normalize song name for comparison (not display).
    Must match the logic in main.py exactly.
    """
    if not song:
        return ""

    normalized = song.lower()

    # Remove accents/diacritics
    normalized = unicodedata.normalize('NFD', normalized)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    # Standardize quotes and apostrophes
    normalized = re.sub(r"[''´`]", "'", normalized)
    normalized = re.sub(r'[""„]', '"', normalized)

    # Normalize various dash characters
    normalized = re.sub(r'[–—−]', '-', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    # Normalize spaces around dashes
    normalized = re.sub(r'\s*-\s*', ' - ', normalized)

    return normalized.strip()


# =============================================================================
# SUPABASE CLIENT
# =============================================================================

def connect_supabase() -> Client:
    """Create Supabase client with service role key."""
    if not SUPABASE_URL:
        raise ValueError("SUPABASE_URL environment variable not set")
    if not SUPABASE_SERVICE_KEY:
        raise ValueError("SUPABASE_SERVICE_KEY environment variable not set")

    return create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


# =============================================================================
# VALIDATION
# =============================================================================

def validate_excel_data(file_path: Path) -> dict:
    """
    Validate Excel data structure.
    Returns dict with validation results.
    """
    print(f"\n{'='*60}")
    print("VALIDATION")
    print(f"{'='*60}")
    print(f"File: {file_path}\n")

    try:
        excel_file = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"ERROR: Could not load file: {e}")
        return {'success': False, 'error': str(e)}

    total_worksheets = 0
    total_columns = 0
    columns_ok = 0
    columns_skipped = 0
    songs_indexed = 0
    songs_skipped = 0
    issues = []

    for sheet_name in excel_file.sheet_names:
        total_worksheets += 1
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

        print(f"  Worksheet: {sheet_name}")
        print(f"    Rows: {len(df)}, Columns: {len(df.columns)}")

        for col_idx in range(1, len(df.columns)):
            total_columns += 1
            seed_value = df.iloc[0, col_idx] if col_idx < len(df.columns) else None

            if pd.isna(seed_value):
                columns_skipped += 1
                matching_songs = df.iloc[2:, col_idx].dropna()
                matching_songs = matching_songs[matching_songs.astype(str).str.strip() != '']
                lost_count = len(matching_songs)
                songs_skipped += lost_count

                if lost_count > 0:
                    issues.append({
                        'worksheet': sheet_name,
                        'column': col_idx,
                        'issue': f'Empty seed track - {lost_count} songs would be lost'
                    })
            else:
                columns_ok += 1
                songs_indexed += 1  # seed track
                matching_songs = df.iloc[2:, col_idx].dropna()
                matching_songs = matching_songs[matching_songs.astype(str).str.strip() != '']
                songs_indexed += len(matching_songs)

    print(f"\n  Summary:")
    print(f"    Worksheets: {total_worksheets}")
    print(f"    Columns OK: {columns_ok}")
    print(f"    Columns skipped: {columns_skipped}")
    print(f"    Songs to index: {songs_indexed}")
    print(f"    Songs skipped: {songs_skipped}")

    if issues:
        print(f"\n  Issues found: {len(issues)}")
        for issue in issues[:5]:
            print(f"    - {issue['worksheet']} col {issue['column']}: {issue['issue']}")
        if len(issues) > 5:
            print(f"    ... and {len(issues) - 5} more")

    return {
        'success': len(issues) == 0,
        'total_worksheets': total_worksheets,
        'total_columns': total_columns,
        'columns_ok': columns_ok,
        'columns_skipped': columns_skipped,
        'songs_indexed': songs_indexed,
        'songs_skipped': songs_skipped,
        'issues': issues
    }


# =============================================================================
# DATA TRANSFORMATION
# =============================================================================

def transform_excel_data(file_path: Path) -> dict:
    """
    Transform Excel data to database format.
    Returns dict with runden, clusters, and songs data.
    """
    print(f"\n{'='*60}")
    print("TRANSFORMING DATA")
    print(f"{'='*60}")

    excel_file = pd.ExcelFile(file_path)

    runden_data = []
    clusters_data = []
    songs_data = []

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

        runden_data.append({
            'name': sheet_name
        })

        for col_idx in range(1, len(df.columns)):
            if pd.isna(df.iloc[0, col_idx]):
                continue

            seed_track = str(df.iloc[0, col_idx]).strip()

            # Get seed contributor from Row 2
            seed_contrib_text = str(df.iloc[1, col_idx]) if pd.notna(df.iloc[1, col_idx]) else ""
            if "Ausgangssong von" in seed_contrib_text:
                seed_contributor = (seed_contrib_text
                    .replace("Ausgangssong von:", "")
                    .replace("Ausgangssong von", "")
                    .strip())
            else:
                seed_contributor = seed_contrib_text.strip()

            cluster_key = f"{sheet_name}_{col_idx}"
            clusters_data.append({
                '_key': cluster_key,
                'runde_name': sheet_name,
                'week_number': col_idx,
                'seed_track': seed_track,
                'seed_contributor': seed_contributor or None
            })

            # Add seed track as song
            songs_data.append({
                '_cluster_key': cluster_key,
                'song_name': seed_track,
                'song_name_normalized': normalize_song_name(seed_track),
                'contributor': seed_contributor or None,
                'is_seed_track': True,
                'row_index': 0
            })

            # Add matching songs
            for idx, cell in enumerate(df.iloc[2:, col_idx].dropna()):
                song_name = str(cell).strip()
                if not song_name:
                    continue

                row_idx = idx + 2
                contributor = str(df.iloc[row_idx, 0]).strip() if pd.notna(df.iloc[row_idx, 0]) else None

                songs_data.append({
                    '_cluster_key': cluster_key,
                    'song_name': song_name,
                    'song_name_normalized': normalize_song_name(song_name),
                    'contributor': contributor,
                    'is_seed_track': False,
                    'row_index': row_idx
                })

    print(f"  Runden: {len(runden_data)}")
    print(f"  Clusters: {len(clusters_data)}")
    print(f"  Songs: {len(songs_data)}")

    return {
        'runden': runden_data,
        'clusters': clusters_data,
        'songs': songs_data
    }


# =============================================================================
# DATABASE OPERATIONS
# =============================================================================

def clear_database(supabase: Client):
    """Clear all existing data (for full refresh)."""
    print("\n  Clearing existing data...")

    # Delete in correct order (foreign key constraints)
    supabase.table("songs").delete().neq("id", 0).execute()
    supabase.table("clusters").delete().neq("id", 0).execute()
    supabase.table("runden").delete().neq("id", 0).execute()

    print("    Done")


def push_data(supabase: Client, data: dict):
    """Push transformed data to Supabase."""
    print(f"\n{'='*60}")
    print("PUSHING TO SUPABASE")
    print(f"{'='*60}")

    clear_database(supabase)

    # Insert runden
    print("\n  Inserting runden...")
    runden_result = supabase.table("runden").insert(data['runden']).execute()
    runden_map = {r['name']: r['id'] for r in runden_result.data}
    print(f"    Inserted {len(runden_result.data)} runden")

    # Insert clusters (resolve runde_name to runde_id)
    print("\n  Inserting clusters...")
    clusters_to_insert = []
    for cluster in data['clusters']:
        clusters_to_insert.append({
            'runde_id': runden_map[cluster['runde_name']],
            'week_number': cluster['week_number'],
            'seed_track': cluster['seed_track'],
            'seed_contributor': cluster['seed_contributor']
        })

    clusters_result = supabase.table("clusters").insert(clusters_to_insert).execute()

    # Build cluster_key -> id mapping
    cluster_map = {}
    for i, cluster in enumerate(data['clusters']):
        cluster_map[cluster['_key']] = clusters_result.data[i]['id']

    print(f"    Inserted {len(clusters_result.data)} clusters")

    # Insert songs (resolve cluster_key to cluster_id)
    print("\n  Inserting songs...")
    songs_to_insert = []
    for song in data['songs']:
        songs_to_insert.append({
            'cluster_id': cluster_map[song['_cluster_key']],
            'song_name': song['song_name'],
            'song_name_normalized': song['song_name_normalized'],
            'contributor': song['contributor'],
            'is_seed_track': song['is_seed_track'],
            'row_index': song['row_index']
        })

    # Batch insert in chunks of 1000
    batch_size = 1000
    total_inserted = 0
    for i in range(0, len(songs_to_insert), batch_size):
        batch = songs_to_insert[i:i + batch_size]
        supabase.table("songs").insert(batch).execute()
        total_inserted += len(batch)
        print(f"    Inserted {total_inserted}/{len(songs_to_insert)} songs...")

    print(f"    Done - {total_inserted} songs inserted")

    # Refresh materialized view
    print("\n  Refreshing search view...")
    try:
        supabase.rpc("refresh_search_view").execute()
        print("    Done")
    except Exception as e:
        print(f"    Warning: Could not refresh view: {e}")
        print("    You may need to run: SELECT refresh_search_view();")


def migrate_likes(supabase: Client):
    """Migrate likes from JSON file to Supabase."""
    print(f"\n{'='*60}")
    print("MIGRATING LIKES")
    print(f"{'='*60}")

    if not LIKES_FILE.exists():
        print(f"  No likes file found at {LIKES_FILE}")
        return

    try:
        with open(LIKES_FILE, 'r', encoding='utf-8') as f:
            likes = json.load(f)
    except Exception as e:
        print(f"  Error reading likes file: {e}")
        return

    if not likes:
        print("  No likes to migrate")
        return

    print(f"  Found {len(likes)} liked songs")

    likes_data = [
        {'song_name': name, 'like_count': count}
        for name, count in likes.items()
    ]

    # Upsert likes
    supabase.table("likes").upsert(likes_data).execute()
    print(f"  Migrated {len(likes_data)} likes to Supabase")


# =============================================================================
# MAIN
# =============================================================================

def find_data_file() -> Path:
    """Find the Excel data file."""
    if not DATA_DIR.exists():
        return None

    excel_files = list(DATA_DIR.glob("*.xlsx"))
    real_files = [f for f in excel_files if "mock" not in f.name.lower()]

    if real_files:
        return real_files[0]
    elif excel_files:
        return excel_files[0]

    return None


def main():
    parser = argparse.ArgumentParser(
        description="Push Excel data to Supabase database",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python push_to_supabase.py                    # Full push
    python push_to_supabase.py --validate-only    # Only validate
    python push_to_supabase.py --dry-run          # Preview changes
    python push_to_supabase.py --migrate-likes    # Include likes

Environment Variables:
    SUPABASE_URL          Your Supabase project URL
    SUPABASE_SERVICE_KEY  Your Supabase service role key
        """
    )

    parser.add_argument('file', nargs='?', help='Path to Excel file (optional)')
    parser.add_argument('--validate-only', action='store_true',
                        help='Only validate Excel file, do not push')
    parser.add_argument('--dry-run', action='store_true',
                        help='Show what would be pushed without making changes')
    parser.add_argument('--migrate-likes', action='store_true',
                        help='Also migrate likes.json to database')
    parser.add_argument('--force', action='store_true',
                        help='Push even if validation has warnings')

    args = parser.parse_args()

    # Find data file
    if args.file:
        file_path = Path(args.file)
    else:
        file_path = find_data_file()

    if not file_path:
        print("ERROR: No Excel file found")
        print("Usage: python push_to_supabase.py [path/to/data.xlsx]")
        sys.exit(1)

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    print(f"\n{'='*60}")
    print("DONNERSTAGSSPIEL - Excel to Supabase Push")
    print(f"{'='*60}")
    print(f"File: {file_path}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Step 1: Validate
    validation = validate_excel_data(file_path)

    if args.validate_only:
        if validation['success']:
            print("\n[OK] Validation passed!")
            sys.exit(0)
        else:
            print("\n[!] Validation found issues")
            sys.exit(1)

    if not validation['success'] and not args.force:
        print("\n[!] Validation found issues. Use --force to push anyway.")
        sys.exit(1)

    # Step 2: Transform
    data = transform_excel_data(file_path)

    if args.dry_run:
        print(f"\n{'='*60}")
        print("DRY RUN - Would push:")
        print(f"{'='*60}")
        print(f"  {len(data['runden'])} runden")
        print(f"  {len(data['clusters'])} clusters")
        print(f"  {len(data['songs'])} songs")
        if args.migrate_likes and LIKES_FILE.exists():
            with open(LIKES_FILE, 'r', encoding='utf-8') as f:
                likes = json.load(f)
            print(f"  {len(likes)} likes")
        print("\nNo changes made.")
        sys.exit(0)

    # Step 3: Connect and push
    try:
        supabase = connect_supabase()
    except ValueError as e:
        print(f"\nERROR: {e}")
        print("\nPlease set environment variables:")
        print("  SUPABASE_URL=https://xxx.supabase.co")
        print("  SUPABASE_SERVICE_KEY=eyJ...")
        print("\nOr create a .env file with these values.")
        sys.exit(1)

    push_data(supabase, data)

    # Step 4: Migrate likes (optional)
    if args.migrate_likes:
        migrate_likes(supabase)

    print(f"\n{'='*60}")
    print("SUCCESS!")
    print(f"{'='*60}")
    print(f"  Pushed {len(data['songs'])} songs to Supabase")
    print(f"\nYour app can now use USE_DATABASE=true to read from Supabase.")


if __name__ == "__main__":
    main()
