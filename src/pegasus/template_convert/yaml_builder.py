"""Convert Excel metadata templates to YAML format."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    import yaml
except ImportError:
    yaml = None

import pandas as pd


def xlsx_to_yaml(xlsx_path: Path | str, output_path: Path | str | None = None) -> dict[str, Any]:
    """Convert Excel metadata template to YAML format.
    
    Args:
        xlsx_path: Path to the Excel file
        output_path: Optional path to save YAML file. If None, returns dict only.
    
    Returns:
        Dictionary with sheet names as keys and data as lists of dicts
    
    Raises:
        ImportError: If PyYAML is not installed
    """
    if yaml is None:
        raise ImportError("PyYAML is required for YAML conversion. Install with: pip install pyyaml")
    
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
        
        # Read sheet with headers from row 1, skip example row
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
            yaml.dump(result, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    return result


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python -m pegasus.template_convert.yaml_builder <xlsx_file> [output_yaml]")
        sys.exit(1)
    
    xlsx_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        result = xlsx_to_yaml(xlsx_file, output_file)
        if not output_file:
            print(yaml.dump(result, default_flow_style=False, allow_unicode=True, sort_keys=False))
    except ImportError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
