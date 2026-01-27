"""Convert Excel metadata templates to JSON format."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def xlsx_to_json(xlsx_path: Path | str, output_path: Path | str | None = None) -> dict[str, Any]:
    """Convert Excel metadata template to JSON format.
    
    Args:
        xlsx_path: Path to the Excel file
        output_path: Optional path to save JSON file. If None, returns dict only.
    
    Returns:
        Dictionary with sheet names as keys and data as lists of dicts
    """
    xlsx_path = Path(xlsx_path)
    if not xlsx_path.exists():
        raise FileNotFoundError(f"Excel file not found: {xlsx_path}")
    
    result: dict[str, Any] = {}
    
    # Read all sheets from Excel
    excel_file = pd.ExcelFile(xlsx_path)
    
    for sheet_name in excel_file.sheet_names:
        # Skip hidden validation sheets
        if sheet_name.lower() == "validation":
            continue
        
        # Read sheet, skipping first 3 rows (description, header, example)
        df = pd.read_excel(excel_file, sheet_name=sheet_name, header=None, skiprows=3)
        
        # Get headers from row 1 (index 1 in original, but we skipped 3 rows)
        # Re-read to get headers properly
        df_with_headers = pd.read_excel(excel_file, sheet_name=sheet_name, header=1)
        # Skip the example row (row 2, index 2)
        df_with_headers = df_with_headers.iloc[1:]
        
        # Convert to list of dicts, removing NaN values
        data = []
        for _, row in df_with_headers.iterrows():
            row_dict = {}
            for col in df_with_headers.columns:
                value = row[col]
                # Convert NaN to None, keep other values
                if pd.isna(value):
                    continue
                row_dict[col] = value
            # Only add non-empty rows
            if row_dict:
                data.append(row_dict)
        
        result[sheet_name] = data
    
    # Save to file if output path provided
    if output_path:
        output_path = Path(output_path)
        with output_path.open("w") as f:
            json.dump(result, f, indent=2, default=str)
    
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m pegasus.template_convert.json_builder <xlsx_file> [output_json]")
        sys.exit(1)
    
    xlsx_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    result = xlsx_to_json(xlsx_file, output_file)
    if not output_file:
        print(json.dumps(result, indent=2, default=str))
