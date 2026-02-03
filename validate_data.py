"""
Data Validation Script for Donnerstagsspieler
Checks Excel data for indexing gaps and reports any columns/songs that would be skipped.
"""
import pandas as pd
from pathlib import Path
import sys


def validate_excel_data(file_path):
    """
    Validate Excel data and report indexing issues.
    Returns: dict with validation results
    """
    print(f"\n{'='*60}")
    print("DATA VALIDATION REPORT")
    print(f"{'='*60}")
    print(f"File: {file_path}\n")

    # Load Excel file
    try:
        excel_file = pd.ExcelFile(file_path)
    except Exception as e:
        print(f"ERROR: Could not load file: {e}")
        return None

    # Statistics
    total_worksheets = 0
    total_columns = 0
    columns_ok = 0
    columns_skipped = 0
    songs_indexed = 0
    songs_skipped = 0

    issues = []  # List of all issues found

    for sheet_name in excel_file.sheet_names:
        total_worksheets += 1
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None)

        print(f"\n--- Worksheet: {sheet_name} ---")
        print(f"    Rows: {len(df)}, Columns: {len(df.columns)}")

        worksheet_issues = []
        worksheet_songs = 0
        worksheet_skipped = 0

        # Check each column (skip Column A which has contributor names)
        for col_idx in range(1, len(df.columns)):
            total_columns += 1
            col_letter = get_column_letter(col_idx)

            # Check if seed track (Row 1) is empty
            seed_value = df.iloc[0, col_idx] if col_idx < len(df.columns) else None

            if pd.isna(seed_value):
                # CRITICAL: Entire column will be skipped
                columns_skipped += 1

                # Count songs that would be lost
                matching_songs = df.iloc[2:, col_idx].dropna()
                matching_songs = matching_songs[matching_songs.astype(str).str.strip() != '']
                lost_songs = matching_songs.tolist()

                songs_skipped += len(lost_songs)
                worksheet_skipped += len(lost_songs)

                issue = {
                    'worksheet': sheet_name,
                    'column': col_letter,
                    'col_idx': col_idx,
                    'type': 'EMPTY_SEED',
                    'lost_songs': lost_songs
                }
                worksheet_issues.append(issue)
                issues.append(issue)

                print(f"    Column {col_letter}: [!] EMPTY SEED TRACK - Column skipped!")
                if lost_songs:
                    print(f"        {len(lost_songs)} songs would be lost:")
                    for i, song in enumerate(lost_songs[:5], 1):
                        print(f"          - {song}")
                    if len(lost_songs) > 5:
                        print(f"          ... and {len(lost_songs) - 5} more")
            else:
                # Column OK - count indexed songs
                columns_ok += 1
                seed_track = str(seed_value).strip()

                # Count seed track
                songs_indexed += 1
                worksheet_songs += 1

                # Count matching songs (Row 3+)
                matching_songs = df.iloc[2:, col_idx].dropna()
                matching_songs = matching_songs[matching_songs.astype(str).str.strip() != '']
                songs_indexed += len(matching_songs)
                worksheet_songs += len(matching_songs)

                # Check for missing contributor in Row 2
                contributor = df.iloc[1, col_idx] if len(df) > 1 else None
                contributor_warning = ""
                if pd.isna(contributor) or str(contributor).strip() == "":
                    contributor_warning = " (no contributor)"

                print(f"    Column {col_letter}: [OK] Seed: \"{seed_track[:40]}\" -> {len(matching_songs)+1} songs{contributor_warning}")

        print(f"    Summary: {worksheet_songs} songs indexed, {worksheet_skipped} songs skipped")

    # Print summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Total worksheets:     {total_worksheets}")
    print(f"  Total columns:        {total_columns}")
    print(f"  Columns OK:           {columns_ok}")
    print(f"  Columns with issues:  {columns_skipped}")
    print(f"  Songs indexed:        {songs_indexed}")
    print(f"  Songs skipped:        {songs_skipped}")

    if issues:
        print(f"\n[!] ISSUES FOUND: {len(issues)} columns have empty seed tracks")
        print("    These columns are completely skipped during indexing.")
        print("    To fix: Add a seed track (Ausgangssong) in Row 1 of each column.")
    else:
        print(f"\n[OK] No issues found! All data will be indexed correctly.")

    return {
        'total_worksheets': total_worksheets,
        'total_columns': total_columns,
        'columns_ok': columns_ok,
        'columns_skipped': columns_skipped,
        'songs_indexed': songs_indexed,
        'songs_skipped': songs_skipped,
        'issues': issues
    }


def get_column_letter(col_idx):
    """Convert column index to Excel-style letter (0=A, 1=B, etc.)"""
    result = ""
    while col_idx >= 0:
        result = chr(col_idx % 26 + ord('A')) + result
        col_idx = col_idx // 26 - 1
    return result


def find_data_file():
    """Find the Excel data file to validate"""
    data_dir = Path("data")

    if not data_dir.exists():
        return None

    excel_files = list(data_dir.glob("*.xlsx"))

    # Prefer real data over mock
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
        print("Usage: python validate_data.py [path/to/data.xlsx]")
        print("       Or place an Excel file in the data/ folder.")
        sys.exit(1)

    if not file_path.exists():
        print(f"ERROR: File not found: {file_path}")
        sys.exit(1)

    result = validate_excel_data(file_path)

    if result and result['songs_skipped'] > 0:
        sys.exit(1)  # Exit with error code if issues found

    sys.exit(0)


if __name__ == "__main__":
    main()
