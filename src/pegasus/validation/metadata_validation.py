"""Simple metadata validation for PEGASUS Excel templates."""

from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

import pandas as pd
from pydantic import BaseModel, ValidationError

from pegasus.schema.core import (
    AnyEvidenceCategory,
    GeneEvidenceCategory,
    VariantEvidenceCategory,
)
from pegasus.schema.peg_metadata_schema.metadata_basic_schema import (
    DatasetDescription,
    GenomicIdentifier,
)
from pegasus.schema.peg_metadata_schema.metadata_evidence_schema import Evidence
from pegasus.schema.peg_metadata_schema.metadata_integration_schme import Integration
from pegasus.schema.peg_metadata_schema.metadata_method_schema import Method
from pegasus.schema.peg_metadata_schema.metadata_source_schema import Source


class PegMetadataValidation:
    """Validate PEGASUS metadata Excel files."""

    def __init__(self, file_path: Path) -> None:
        self.file_path = file_path
        self.errors: list[dict] = []
        self.sheet_data: dict[str, Any] = {}
        self.sheet_models = {
            "DatasetDescription": DatasetDescription,
            "GenomicIdentifier": GenomicIdentifier,
            "Evidence": Evidence,
            "Integration": Integration,
            "Source": Source,
            "Method": Method,
        }

    def validate_metadata(self, error_limit: int = 50) -> list[dict]:
        """Validate the metadata Excel file."""
        try:
            # Suppress openpyxl data validation warning
            with warnings.catch_warnings():
                warnings.filterwarnings("ignore", message=".*Data Validation extension is not supported.*")
                excel_file = pd.ExcelFile(self.file_path)
        except Exception as e:
            self.errors.append({
                "step": "File Reading",
                "type": "error",
                "message": f"Could not read Excel file: {e}",
            })
            return self.errors
        
        # Check required sheets exist
        available_sheets = {name.lower().strip(): name for name in excel_file.sheet_names}
        missing_sheets = [
            name for name in self.sheet_models if name.lower().strip() not in available_sheets
        ]

        if missing_sheets:
            self.errors.append({
                "step": "Sheet Validation",
                "type": "error",
                "message": f"Missing required sheets: {missing_sheets}",
            })
            return self.errors
        
        # Validate each sheet
        for sheet_name, model in self.sheet_models.items():
            sheet_key = sheet_name.lower().strip()
            
            if sheet_key not in available_sheets:
                continue
            
            data = self._validate_sheet(
                excel_file, available_sheets[sheet_key], model, error_limit
            )
            self.sheet_data[sheet_name] = data

        # Cross-sheet validation
        self._validate_cross_sheet()

        return self.errors

    def _validate_sheet(
        self,
        excel_file: pd.ExcelFile,
        sheet_name: str,
        model: type[BaseModel],
        error_limit: int,
    ) -> dict[str, Any]:
        """Validate a single sheet."""
        # Read sheet (skip first 3 rows: description, header, example)
        try:
            df = pd.read_excel(excel_file, sheet_name=sheet_name, header=1)
            df = df.iloc[1:]  # Skip example row
            df = df.dropna(how="all")  # Remove completely empty rows
        except Exception as e:
            self.errors.append({
                "step": f"{sheet_name} - Sheet Reading",
                "type": "error",
                "message": f"Could not read sheet: {e}",
            })
            return {
                "records": [],
                "valid_records": [],
                "found_fields": set(),
                "required_fields": set(),
            }

        # Build header mapping
        header_map = {}
        for field_name, field in model.model_fields.items():
            extra = field.json_schema_extra or {}
            header = str(extra.get("header", field_name))
            header_map[header.lower()] = field_name
            header_map[str(field_name).lower()] = field_name

        # Map columns
        column_map = {}
        unknown_cols = []
        for col in df.columns:
            if pd.isna(col) or str(col).startswith("Unnamed"):
                continue
            col_str = str(col).strip() if col is not None else ""
            col_lower = col_str.lower()
            field_name = header_map.get(col_lower)
            if field_name:
                column_map[col] = field_name
            else:
                unknown_cols.append(str(col))

        # Check for missing required fields
        required_fields = {
            name
            for name, field in model.model_fields.items()
            if field.is_required() and field.default is None
        }
        found_fields = set(column_map.values())
        missing_required = required_fields - found_fields

        if missing_required:
            self.errors.append({
                "step": f"{sheet_name} - Header Validation",
                "type": "error",
                "message": f"Missing required columns: {sorted(missing_required)}",
            })
            return {
                "records": [],
                "valid_records": [],
                "found_fields": set(),
                "required_fields": required_fields,
            }

        if unknown_cols:
            self.errors.append({
                "step": f"{sheet_name} - Header Validation",
                "type": "warning",
                "message": f"Unknown columns (ignored): {unknown_cols}",
            })
        else:
            self.errors.append({
                "step": f"{sheet_name} - Header Validation",
                "type": "info",
                "message": "All required columns found.",
            })

        # Rename columns and validate rows
        df = df.rename(columns=column_map)
        df = df[[c for c in df.columns if c in found_fields]]
        df = self._drop_prefilled_rows(sheet_name, df)

        records = []
        valid_records = []
        row_errors = []

        for idx, row in df.iterrows():
            record = {}
            for field_name in found_fields:
                value = row.get(field_name)
                if pd.isna(value):
                    record[field_name] = None
                else:
                    # Simple bool coercion
                    if isinstance(value, str) and value.strip().lower() in ("true", "yes"):
                        record[field_name] = True
                    elif isinstance(value, str) and value.strip().lower() in ("false", "no"):
                        record[field_name] = False
                    else:
                        record[field_name] = value

            if not any(v is not None for v in record.values()):
                continue  # Skip completely empty rows

            records.append(record)

            try:
                model.model_validate(record)
                valid_records.append(record)
            except ValidationError as exc:
                row_errors.append({
                    "row": int(idx) + 4,  # +1 for 0-index, +1 for header, +1 for example, +1 for 1-based
                    "error": [{"loc": list(e.get("loc", [])), "msg": e.get("msg", "")} for e in exc.errors()],
                })
                if len(row_errors) >= error_limit:
                    break

        if row_errors:
            self.errors.append({
                "step": f"{sheet_name} - Row Validation",
                "type": "error",
                "message": "Validation failed for one or more rows.",
                "details": row_errors,
            })
        else:
            self.errors.append({
                "step": f"{sheet_name} - Row Validation",
                "type": "info",
                "message": "All rows validated successfully.",
            })

        return {
            "records": records,
            "valid_records": valid_records,
            "found_fields": found_fields,
            "required_fields": required_fields,
        }

    @staticmethod
    def _drop_prefilled_rows(sheet_name: str, df: pd.DataFrame) -> pd.DataFrame:
        if sheet_name.lower().strip() != "evidence":
            return df
        if "evidence_category" not in df.columns:
            return df
        mask = df["evidence_category"].apply(
            lambda v: not (
                pd.isna(v)
                or str(v).strip() in {"0", "0.0"}
            )
        )
        return df[mask]

    def cross_check_column_names(self) -> dict[str, list[str]]:
        """Return the column names of a specific sheet."""
        headers: dict[str, list[str]] = {}
        headers["Evidence"] = [column.get("column_header")
                   for column in self.sheet_data.get("Evidence", {}).get("records", [])
                   ]
        headers["Integration"] = [column.get("column_header")
                   for column in self.sheet_data.get("Integration", {}).get("records", [])
                   ]
        return headers
    
    def return_author_conclusion_rows(self) -> list[dict]:
        """Return rows with author_conclusion=TRUE in Integration sheet."""
        integration_data = self.sheet_data.get("Integration", {}).get("records", [])
        author_conclusion_rows = [
            row for row in integration_data if row.get("author_conclusion") is True
        ]
        
        if len(author_conclusion_rows) != 1:
            raise ValueError(
                f"Expected exactly one author_conclusion=TRUE row, found {len(author_conclusion_rows)}"
                )
        
        return author_conclusion_rows

    def _validate_cross_sheet(self) -> None:
        """Validate cross-sheet references."""
        evidence = self.sheet_data.get("Evidence", {}).get("valid_records", [])
        integration = self.sheet_data.get("Integration", {}).get("valid_records", [])
        source = self.sheet_data.get("Source", {}).get("valid_records", [])
        method = self.sheet_data.get("Method", {}).get("valid_records", [])

        # Check row counts
        if len(evidence) <= 2:
            self.errors.append({
                "step": "Evidence - Row Count",
                "type": "error",
                "message": f"Evidence must have more than 2 rows. Found {len(evidence)}.",
            })

        if len(integration) <= 1:
            self.errors.append({
                "step": "Integration - Row Count",
                "type": "error",
                "message": f"Integration must have more than 1 row. Found {len(integration)}.",
            })

        # Check author_conclusion
        author_conclusion_count = sum(
            1 for r in integration if r.get("author_conclusion") is True
        )
        if author_conclusion_count != 1:
            self.errors.append({
                "step": "Integration - Author Conclusion",
                "type": "error",
                "message": f"Exactly one row must have author_conclusion=TRUE. Found {author_conclusion_count}.",
            })

        # Check tag references
        source_tags = {r.get("source_tag") for r in source if r.get("source_tag")}
        method_tags = {r.get("method_tag") for r in method if r.get("method_tag")}

        evidence_source_tags = {r.get("source_tag") for r in evidence if r.get("source_tag")}
        evidence_method_tags = {r.get("method_tag") for r in evidence if r.get("method_tag")}
        integration_method_tags = {r.get("method_tag") for r in integration if r.get("method_tag")}

        missing_source = sorted(evidence_source_tags - source_tags)
        if missing_source:
            self.errors.append({
                "step": "Evidence - Tag Reference",
                "type": "error",
                "message": f"source_tag values used in Evidence but missing from Source: {missing_source}",
            })

        missing_method = sorted((evidence_method_tags | integration_method_tags) - method_tags)
        if missing_method:
            self.errors.append({
                "step": "Integration - Tag Reference",
                "type": "error",
                "message": f"method_tag values used but missing from Method: {missing_method}",
            })

# Test code (remove in production)
if __name__ == "__main__":
    test = PegMetadataValidation(file_path=Path("/Users/yueji/Documents/GitHub/PEGASUS_metadata_template/test_data/metadata_peg.xlsx"))
    print(test.validate_metadata())
