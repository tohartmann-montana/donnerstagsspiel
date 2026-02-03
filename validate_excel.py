"""
Validate Excel file structure for Donnerstagsspieler app
Checks if the structure matches what the app expects
"""
import pandas as pd
from pathlib import Path
import sys

def validate_excel_structure(file_path):
    """
    Validate the Excel file structure and provide detailed analysis
    """
    print("=" * 70)
    print("Excel Structure Validation")
    print("=" * 70)

    try:
        excel_file = pd.ExcelFile(file_path)
        print(f"\nFile: {file_path}")
        print(f"Number of sheets: {len(excel_file.sheet_names)}")
        print(f"Sheet names: {', '.join(excel_file.sheet_names)}")

        # Analyze first sheet in detail
        first_sheet = excel_file.sheet_names[0]
        print(f"\n--- Analyzing Sheet: '{first_sheet}' ---")

        df = pd.read_excel(excel_file, sheet_name=first_sheet, header=None)

        print(f"\nDimensions: {df.shape[0]} rows x {df.shape[1]} columns")

        print("\n--- First 10 rows x 5 columns ---")
        print(df.iloc[:10, :5].to_string())

        print("\n--- Structure Analysis ---")

        # Check Row 1
        print("\nRow 1 (Expected: Ausgangssongs):")
        print(f"  A1: {df.iloc[0, 0]}")
        print(f"  B1: {df.iloc[0, 1] if len(df.columns) > 1 else 'N/A'}")
        print(f"  C1: {df.iloc[0, 2] if len(df.columns) > 2 else 'N/A'}")

        # Check Row 2
        print("\nRow 2 (Expected: 'Ausgangssong von: Name'):")
        print(f"  A2: {df.iloc[1, 0] if len(df) > 1 else 'N/A'}")
        print(f"  B2: {df.iloc[1, 1] if len(df) > 1 and len(df.columns) > 1 else 'N/A'}")
        print(f"  C2: {df.iloc[1, 2] if len(df) > 1 and len(df.columns) > 2 else 'N/A'}")

        # Check Row 3
        print("\nRow 3 (Expected: First contributor name in A, first matching songs in B+):")
        print(f"  A3: {df.iloc[2, 0] if len(df) > 2 else 'N/A'}")
        print(f"  B3: {df.iloc[2, 1] if len(df) > 2 and len(df.columns) > 1 else 'N/A'}")
        print(f"  C3: {df.iloc[2, 2] if len(df) > 2 and len(df.columns) > 2 else 'N/A'}")

        # Check Row 4
        print("\nRow 4:")
        print(f"  A4: {df.iloc[3, 0] if len(df) > 3 else 'N/A'}")
        print(f"  B4: {df.iloc[3, 1] if len(df) > 3 and len(df.columns) > 1 else 'N/A'}")

        # Count non-empty cells in each row
        print("\n--- Non-empty cells per row (first 10 rows) ---")
        for i in range(min(10, len(df))):
            non_empty = df.iloc[i].notna().sum()
            print(f"Row {i+1}: {non_empty} non-empty cells")

        # Count non-empty cells in each column
        print("\n--- Non-empty cells per column (first 10 columns) ---")
        for i in range(min(10, len(df.columns))):
            non_empty = df.iloc[:, i].notna().sum()
            col_letter = chr(65 + i)  # A, B, C, etc.
            print(f"Column {col_letter}: {non_empty} non-empty cells")

        # Detect potential issues
        print("\n--- Structure Validation ---")
        issues = []

        # Check if Row 1, Col A is empty (expected)
        if pd.notna(df.iloc[0, 0]):
            issues.append("WARNING: A1 should be empty but contains: '{}'".format(df.iloc[0, 0]))

        # Check if Row 2 contains "Ausgangssong von" pattern
        row2_has_pattern = False
        if len(df) > 1:
            for col_idx in range(1, min(5, len(df.columns))):
                cell_value = str(df.iloc[1, col_idx])
                if "Ausgangssong von" in cell_value or "von:" in cell_value.lower():
                    row2_has_pattern = True
                    break

        if not row2_has_pattern:
            issues.append("WARNING: Row 2 doesn't contain 'Ausgangssong von' pattern")

        # Summary
        print("\n" + "=" * 70)
        if issues:
            print("VALIDATION RESULT: STRUCTURE MISMATCH DETECTED")
            print("=" * 70)
            for issue in issues:
                print(f"  - {issue}")
            print("\nThis file may need reformatting to work with the app.")
        else:
            print("VALIDATION RESULT: Structure looks compatible!")
            print("=" * 70)

        return df, issues

    except Exception as e:
        print(f"\nERROR: Failed to read Excel file: {e}")
        return None, [str(e)]

if __name__ == "__main__":
    # Check if file path provided
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # Default to looking in data folder
        data_folder = Path("data")
        excel_files = list(data_folder.glob("*.xlsx"))

        # Filter out mock data
        excel_files = [f for f in excel_files if "mock" not in f.name.lower()]

        if excel_files:
            file_path = excel_files[0]
            print(f"No file specified, using: {file_path}")
        else:
            print("ERROR: No Excel file found in data/ folder")
            print("Usage: python validate_excel.py <path_to_excel_file>")
            sys.exit(1)

    df, issues = validate_excel_structure(file_path)

    if issues:
        print("\nNext steps:")
        print("1. Check if the file structure matches the expected format")
        print("2. If not, we may need to convert/reformat the data")
        print("3. Or modify the app to handle this specific structure")
