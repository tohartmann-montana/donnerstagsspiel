"""
Performance benchmark for Donnerstagsspieler optimizations
"""
import time
import pandas as pd
from pathlib import Path
from main import load_excel_data, build_song_index, search_songs, get_song_connections

def benchmark():
    print("=" * 60)
    print("Performance Benchmark - Donnerstagsspieler")
    print("=" * 60)

    # Load data
    print("\n1. Loading Excel data...")
    start = time.time()
    excel_files = list(Path("data").glob("*.xlsx"))
    if not excel_files:
        print("ERROR: No Excel files found in data/ directory")
        return

    database_file = excel_files[0]
    worksheets = load_excel_data(database_file)
    load_time = time.time() - start

    # Count songs
    total_songs = 0
    for df in worksheets.values():
        for col_idx in range(1, len(df.columns)):
            seed_count = 1 if pd.notna(df.iloc[0, col_idx]) else 0
            matching_count = df.iloc[2:, col_idx].dropna().shape[0]
            total_songs += seed_count + matching_count

    print(f"   OK Loaded {len(worksheets)} worksheets with {total_songs} songs")
    print(f"   OK Time: {load_time:.3f}s")

    # Build song index
    print("\n2. Building song index (cached function)...")
    start = time.time()
    song_index = build_song_index(worksheets)
    index_time = time.time() - start
    print(f"   OK Indexed {len(song_index)} unique songs")
    print(f"   OK Time: {index_time:.3f}s")

    # Test search performance
    print("\n3. Testing search performance...")
    test_queries = [
        "rock",
        "love",
        "party",
        "summer",
        "night"
    ]

    search_times = []
    for query in test_queries:
        start = time.time()
        results = search_songs(query, song_index, fuzzy_threshold=70)
        search_time = time.time() - start
        search_times.append(search_time)
        print(f"   Query: '{query}' -> {len(results)} results in {search_time:.3f}s")

    avg_search_time = sum(search_times) / len(search_times)
    print(f"   OK Average search time: {avg_search_time:.3f}s")

    # Test song connections performance
    print("\n4. Testing song connections lookup...")

    # Get a few sample songs
    sample_songs = list(song_index.keys())[:5]
    connection_times = []

    for song in sample_songs:
        start = time.time()
        connections = get_song_connections(song, song_index)
        conn_time = time.time() - start
        connection_times.append(conn_time)
        print(f"   Song: '{song[:40]}...' -> {len(connections)} clusters in {conn_time:.4f}s")

    avg_conn_time = sum(connection_times) / len(connection_times)
    print(f"   OK Average connection lookup: {avg_conn_time:.4f}s")

    # Summary
    print("\n" + "=" * 60)
    print("PERFORMANCE SUMMARY")
    print("=" * 60)
    print(f"Dataset size: {total_songs} songs across {len(worksheets)} worksheets")
    print(f"Index build time: {index_time:.3f}s (one-time, cached)")
    print(f"Average search time: {avg_search_time:.3f}s")
    print(f"Average connection lookup: {avg_conn_time:.4f}s")

    # Performance targets
    print("\n" + "=" * 60)
    print("TARGET vs ACTUAL")
    print("=" * 60)

    search_target = 1.0
    conn_target = 0.5

    search_status = "OK PASS" if avg_search_time < search_target else "FAIL FAIL"
    conn_status = "OK PASS" if avg_conn_time < conn_target else "FAIL FAIL"

    print(f"Search time target: <{search_target}s -> Actual: {avg_search_time:.3f}s {search_status}")
    print(f"Connection lookup target: <{conn_target}s -> Actual: {avg_conn_time:.4f}s {conn_status}")

    print("\n" + "=" * 60)

if __name__ == "__main__":
    benchmark()
