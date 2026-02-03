"""
Duplicate Song Detection Report for Donnerstagsspieler
Finds songs with multiple spelling variants in the Excel data.
"""
import pandas as pd
from pathlib import Path
import sys
import unicodedata
import re
from collections import defaultdict


def normalize_song_name(song: str) -> str:
    """
    Normalize song name for comparison (not display).
    Same logic as in main.py for consistency.
    """
    if not song:
        return ""

    # Convert to lowercase
    normalized = song.lower()

    # Remove accents/diacritics
    normalized = unicodedata.normalize('NFD', normalized)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')

    # Standardize quotes and apostrophes
    normalized = re.sub(r"[''`]", "'", normalized)
    normalized = re.sub(r'["""]', '"', normalized)

    # Normalize various dash characters
    normalized = re.sub(r'[-]', '-', normalized)

    # Collapse multiple spaces
    normalized = re.sub(r'\s+', ' ', normalized)

    # Normalize spaces around dashes
    normalized = re.sub(r'\s*-\s*', ' - ', normalized)

    # Strip whitespace
    normalized = normalized.strip()

    return normalized


def find_duplicates(file_path):
    """
    Find all songs with multiple spelling variants.
    Returns: dict of normalized_name -> {variants: list, locations: list}
    """
    print(f"\n{'='*60}")
    print("DUPLICATE SONG REPORT")
    print(f"{'='*60}")
    print(f"File: {file_path}\n")

    # Load Excel file
    try:
        excel_file = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"ERROR: Could not load file: {e}")
        return None

    # Build index: normalized_name -> {variants: set, locations: list}
    song_index = defaultdict(lambda: {'variants': set(), 'locations': []})

    total_songs = 0

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

        for col_idx in range(1, len(df.columns)):
            # Skip empty seed tracks
            if pd.isna(df.iloc[0, col_idx]):
                continue

            # Get seed track
            seed_track = str(df.iloc[0, col_idx]).strip()
            if seed_track:
                normalized = normalize_song_name(seed_track)
                song_index[normalized]['variants'].add(seed_track)
                song_index[normalized]['locations'].append(f"{sheet_name}, Woche {col_idx}")
                total_songs += 1

            # Get matching songs (Row 3+)
            column_data = df.iloc[2:, col_idx].dropna()
            column_data = column_data[column_data.astype(str).str.strip() != ''].astype(str)

            for song in column_data.tolist():
                song = song.strip()
                if song:
                    normalized = normalize_song_name(song)
                    song_index[normalized]['variants'].add(song)
                    song_index[normalized]['locations'].append(f"{sheet_name}, Woche {col_idx}")
                    total_songs += 1

    # Find entries with multiple variants
    duplicates = {}
    for normalized, data in song_index.items():
        if len(data['variants']) > 1:
            duplicates[normalized] = {
                'variants': sorted(list(data['variants'])),
                'locations': data['locations']
            }

    # Sort by number of variants (most first)
    sorted_duplicates = sorted(
        duplicates.items(),
        key=lambda x: len(x[1]['variants']),
        reverse=True
    )

    # Print report
    if sorted_duplicates:
        print(f"Found {len(sorted_duplicates)} songs with multiple spellings:\n")

        for idx, (normalized, data) in enumerate(sorted_duplicates, 1):
            variants = data['variants']
            locations = data['locations']

            # Count unique locations per variant
            print(f"{idx}. \"{normalized}\" ({len(variants)} variants):")
            for variant in variants:
                # Count how many times this exact variant appears
                variant_count = sum(1 for loc in locations
                                   if any(v == variant for v in song_index[normalized]['variants']))
                print(f"   - \"{variant}\"")

            # Show sample locations
            unique_locations = sorted(set(locations))[:3]
            if len(unique_locations) < len(set(locations)):
                print(f"   Locations: {', '.join(unique_locations)} ... (+{len(set(locations)) - 3} more)")
            else:
                print(f"   Locations: {', '.join(unique_locations)}")
            print()

    # Summary
    print(f"{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Total song entries:                {total_songs}")
    print(f"  Unique songs (after normalization): {len(song_index)}")
    print(f"  Songs with multiple spellings:      {len(duplicates)}")

    total_variant_entries = sum(len(d['variants']) for d in duplicates.values())
    print(f"  Total variant entries:              {total_variant_entries}")

    if duplicates:
        print(f"\n[!] {len(duplicates)} songs have inconsistent spellings.")
        print("    Consider standardizing these in the Excel file.")
    else:
        print(f"\n[OK] No duplicate spellings found!")

    return {
        'total_songs': total_songs,
        'unique_songs': len(song_index),
        'songs_with_variants': len(duplicates),
        'duplicates': dict(sorted_duplicates)
    }


def find_data_file():
    """Find the Excel data file"""
    data_dir = Path("data")

    if not data_dir.exists():
        return None

    excel_files = list(data_dir.glob("*.xlsx"))
    real_files = [f for f in excel_files if "mock" not in f.name.lower()]

    if real_files:
        return real_files[0]
    elif excel_files:
        return excel_files[0]

    return None


def main():
    # Get file path from command line or find automatically
    if len(sys.argv) > 1:
        file_path = Path(sys.argv[1])
    else:
        file_path = find_data_file()

    if not file_path:
        print("ERROR: No Excel file found.")
        print("Usage: python find_duplicates.py [path/to/data.xlsx]")
        sys.exit(1)

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    result = find_duplicates(file_path)

    if result and result['songs_with_variants'] > 0:
        sys.exit(1)  # Exit with error code if duplicates found

    sys.exit(0)


if __name__ == "__main__":
    main()
