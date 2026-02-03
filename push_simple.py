"""
Simple Excel to Supabase Push Script
Uses requests directly to avoid Python 3.14 compatibility issues.
"""

import os
import json
import unicodedata
import re
import time
from pathlib import Path
from dotenv import load_dotenv
import requests
import pandas as pd

load_dotenv()

# Configuration
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")
DATA_DIR = Path("data")


def normalize_song_name(song: str) -> str:
    """Normalize song name for comparison."""
    if not song:
        return ""
    normalized = song.lower()
    normalized = unicodedata.normalize('NFD', normalized)
    normalized = ''.join(c for c in normalized if unicodedata.category(c) != 'Mn')
    normalized = re.sub(r"[''´`]", "'", normalized)
    normalized = re.sub(r'[""„]', '"', normalized)
    normalized = re.sub(r'[–—−]', '-', normalized)
    normalized = re.sub(r'\s+', ' ', normalized)
    normalized = re.sub(r'\s*-\s*', ' - ', normalized)
    return normalized.strip()


def supabase_request(method, table, data=None, params=None, retries=3):
    """Make a request to Supabase REST API with retry logic."""
    url = f"{SUPABASE_URL}/rest/v1/{table}"
    headers = {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation"
    }

    for attempt in range(retries):
        try:
            if method == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=30)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data, timeout=60)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers, params=params, timeout=30)
            else:
                raise ValueError(f"Unknown method: {method}")

            if response.status_code >= 400:
                print(f"Error {response.status_code}: {response.text[:200]}")
                return None

            try:
                return response.json() if response.text else []
            except:
                return response.text

        except (requests.exceptions.RequestException, ConnectionError) as e:
            if attempt < retries - 1:
                wait = (attempt + 1) * 2
                print(f"  Connection error, retrying in {wait}s... ({attempt + 1}/{retries})")
                time.sleep(wait)
            else:
                print(f"  Failed after {retries} attempts: {e}")
                return None


def test_connection():
    """Test Supabase connection."""
    print("Testing connection to Supabase...")
    print(f"URL: {SUPABASE_URL}")
    print(f"Key: {SUPABASE_KEY[:20]}..." if SUPABASE_KEY else "Key: NOT SET")

    result = supabase_request("GET", "runden", params={"select": "id", "limit": "1"})
    if result is not None:
        print("[OK] Connection successful!")
        return True
    else:
        print("[FAIL] Connection failed!")
        return False


def clear_data():
    """Clear existing data."""
    print("\nClearing existing data...")
    # Delete in order: songs -> clusters -> runden
    supabase_request("DELETE", "songs", params={"id": "gt.0"})
    supabase_request("DELETE", "clusters", params={"id": "gt.0"})
    supabase_request("DELETE", "runden", params={"id": "gt.0"})
    print("  Done")


def push_data(file_path: Path):
    """Transform and push Excel data to Supabase."""
    print(f"\nLoading {file_path}...")
    excel_file = pd.ExcelFile(file_path)

    # Collect all data
    runden_data = []
    clusters_data = []
    songs_data = []

    for sheet_name in excel_file.sheet_names:
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)
        runden_data.append({'name': sheet_name})

        for col_idx in range(1, len(df.columns)):
            if pd.isna(df.iloc[0, col_idx]):
                continue

            seed_track = str(df.iloc[0, col_idx]).strip()
            seed_contrib_text = str(df.iloc[1, col_idx]) if pd.notna(df.iloc[1, col_idx]) else ""

            if "Ausgangssong von" in seed_contrib_text:
                seed_contributor = seed_contrib_text.replace("Ausgangssong von:", "").replace("Ausgangssong von", "").strip()
            else:
                seed_contributor = seed_contrib_text.strip()

            clusters_data.append({
                '_runde_name': sheet_name,
                'week_number': col_idx,
                'seed_track': seed_track,
                'seed_contributor': seed_contributor or None
            })

            # Seed track as song
            songs_data.append({
                '_cluster_key': f"{sheet_name}_{col_idx}",
                'song_name': seed_track,
                'song_name_normalized': normalize_song_name(seed_track),
                'contributor': seed_contributor or None,
                'is_seed_track': True,
                'row_index': 0
            })

            # Matching songs
            for idx, cell in enumerate(df.iloc[2:, col_idx].dropna()):
                song_name = str(cell).strip()
                if not song_name:
                    continue
                row_idx = idx + 2
                contributor = str(df.iloc[row_idx, 0]).strip() if pd.notna(df.iloc[row_idx, 0]) else None

                songs_data.append({
                    '_cluster_key': f"{sheet_name}_{col_idx}",
                    'song_name': song_name,
                    'song_name_normalized': normalize_song_name(song_name),
                    'contributor': contributor,
                    'is_seed_track': False,
                    'row_index': row_idx
                })

    print(f"  Runden: {len(runden_data)}")
    print(f"  Clusters: {len(clusters_data)}")
    print(f"  Songs: {len(songs_data)}")

    # Clear and insert
    clear_data()

    # Insert runden
    print("\nInserting runden...")
    runden_result = supabase_request("POST", "runden", data=runden_data)
    if not runden_result:
        print("Failed to insert runden!")
        return False
    runden_map = {r['name']: r['id'] for r in runden_result}
    print(f"  Inserted {len(runden_result)} runden")

    # Insert clusters
    print("\nInserting clusters...")
    clusters_to_insert = []
    for c in clusters_data:
        clusters_to_insert.append({
            'runde_id': runden_map[c['_runde_name']],
            'week_number': c['week_number'],
            'seed_track': c['seed_track'],
            'seed_contributor': c['seed_contributor']
        })

    # Batch insert clusters
    batch_size = 500
    cluster_results = []
    for i in range(0, len(clusters_to_insert), batch_size):
        batch = clusters_to_insert[i:i + batch_size]
        result = supabase_request("POST", "clusters", data=batch)
        if result:
            cluster_results.extend(result)
        print(f"  Inserted {len(cluster_results)}/{len(clusters_to_insert)} clusters...")

    # Build cluster key -> id mapping
    cluster_map = {}
    for i, c in enumerate(clusters_data):
        cluster_map[c['_runde_name'] + "_" + str(c['week_number'])] = cluster_results[i]['id']

    # Insert songs
    print("\nInserting songs...")
    songs_to_insert = []
    for s in songs_data:
        songs_to_insert.append({
            'cluster_id': cluster_map[s['_cluster_key']],
            'song_name': s['song_name'],
            'song_name_normalized': s['song_name_normalized'],
            'contributor': s['contributor'],
            'is_seed_track': s['is_seed_track'],
            'row_index': s['row_index']
        })

    # Batch insert songs with smaller batches and delays
    song_batch_size = 100  # Smaller batches for reliability
    total_inserted = 0
    for i in range(0, len(songs_to_insert), song_batch_size):
        batch = songs_to_insert[i:i + song_batch_size]
        result = supabase_request("POST", "songs", data=batch)
        if result:
            total_inserted += len(result)
        else:
            print(f"  Warning: batch {i // song_batch_size + 1} may have failed")
        print(f"  Inserted {total_inserted}/{len(songs_to_insert)} songs...")
        time.sleep(0.3)  # Small delay between batches

    print(f"\n[OK] SUCCESS! Pushed {total_inserted} songs to Supabase")
    return True


def main():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("ERROR: Set SUPABASE_URL and SUPABASE_SERVICE_KEY in .env file")
        return

    # Find data file
    excel_files = list(DATA_DIR.glob("*.xlsx"))
    real_files = [f for f in excel_files if "mock" not in f.name.lower()]
    file_path = real_files[0] if real_files else (excel_files[0] if excel_files else None)

    if not file_path:
        print("ERROR: No Excel file found in data/")
        return

    print("=" * 60)
    print("DONNERSTAGSSPIEL - Push to Supabase")
    print("=" * 60)

    if not test_connection():
        return

    push_data(file_path)


if __name__ == "__main__":
    main()
