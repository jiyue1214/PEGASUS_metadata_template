import sys
import tempfile
import unittest
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from typing import get_args, get_origin

import pandas as pd

repo_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(repo_root / "src"))

from pegasus.validation.metadata_validation import PegMetadataValidation
from pegasus.schema.peg_metadata_schema.metadata_basic_schema import (
    DatasetDescription,
    GenomicIdentifier,
)
from pegasus.schema.peg_metadata_schema.metadata_evidence_schema import Evidence
from pegasus.schema.peg_metadata_schema.metadata_integration_schme import Integration
from pegasus.schema.peg_metadata_schema.metadata_method_schema import Method
from pegasus.schema.peg_metadata_schema.metadata_source_schema import Source


def _fallback_value(annotation: Any) -> Any:
    ann = annotation
    origin = get_origin(ann)
    args = get_args(ann)
    if origin is not None and str(origin).endswith("Annotated"):
        ann = args[0]
        origin = get_origin(ann)
        args = get_args(ann)
    if origin is not None and str(origin).endswith("Union"):
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            ann = non_none[0]
            origin = get_origin(ann)
            args = get_args(ann)
    if origin is not None and str(origin).endswith("Literal"):
        return args[0]
    try:
        if isinstance(ann, type) and issubclass(ann, Enum):
            return list(ann)[0].value
    except Exception:
        pass
    if ann is bool:
        return True
    if ann is int:
        return 1
    if ann is float:
        return 0.1
    if ann is str:
        return "value"
    name = getattr(ann, "__name__", "")
    if name == "HttpUrl":
        return "https://example.com"
    return "value"


def _example_row(model: type) -> Dict[str, Any]:
    row: Dict[str, Any] = {}
    for field_name, field in model.model_fields.items():
        extra = field.json_schema_extra or {}
        header = extra.get("header", field_name)
        if "example" in extra:
            value = extra["example"]
        else:
            value = _fallback_value(field.annotation)
        row[str(header)] = value
    if model is Evidence:
        row["evidence_category"] = "Molecular QTL"
        row["evidence_category_abbreviation"] = "Molecular QTL"
        row["variant_or_gene_centric"] = "variant-centric"
    if model is Integration:
        row["author_conclusion"] = False
    return row


def _build_sheet_df(model: type, overrides: List[Dict[str, Any]]) -> pd.DataFrame:
    base = _example_row(model)
    rows = []
    for override in overrides:
        row = dict(base)
        row.update(override)
        rows.append(row)
    return pd.DataFrame(rows)


def _write_metadata_excel(
    path: Path,
    evidence_rows: List[Dict[str, Any]],
    integration_rows: List[Dict[str, Any]],
    source_rows: Optional[List[Dict[str, Any]]] = None,
    method_rows: Optional[List[Dict[str, Any]]] = None,
) -> None:
    dataset_df = _build_sheet_df(DatasetDescription, [{}])
    genomic_df = _build_sheet_df(GenomicIdentifier, [{}])
    evidence_df = _build_sheet_df(Evidence, evidence_rows)
    integration_df = _build_sheet_df(Integration, integration_rows)
    source_df = _build_sheet_df(Source, source_rows or [{}])
    method_df = _build_sheet_df(Method, method_rows or [{}])

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        dataset_df.to_excel(writer, sheet_name="DatasetDescription", index=False, startrow=1)
        genomic_df.to_excel(writer, sheet_name="GenomicIdentifier", index=False, startrow=1)
        evidence_df.to_excel(writer, sheet_name="Evidence", index=False, startrow=1)
        integration_df.to_excel(writer, sheet_name="Integration", index=False, startrow=1)
        source_df.to_excel(writer, sheet_name="Source", index=False, startrow=1)
        method_df.to_excel(writer, sheet_name="Method", index=False, startrow=1)


def _has_step(results: List[Dict[str, Any]], step: str) -> bool:
    return any(result.get("step") == step for result in results)


class TestMetadataValidation(unittest.TestCase):
    def test_evidence_requires_more_than_two_valid_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=[
                    {"column_header": "EV1"},
                    {"column_header": "EV2"},
                ],
                integration_rows=[
                    {"column_header": "INT1", "author_conclusion": True},
                    {"column_header": "INT2", "author_conclusion": False},
                ],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Evidence - Row Count Validation"))

    def test_integration_requires_more_than_one_valid_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=[
                    {"column_header": "EV1"},
                    {"column_header": "EV2"},
                    {"column_header": "EV3"},
                ],
                integration_rows=[
                    {"column_header": "INT1", "author_conclusion": True},
                ],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Row Count Validation"))

    def test_author_conclusion_requires_exactly_one_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=[
                    {"column_header": "EV1"},
                    {"column_header": "EV2"},
                    {"column_header": "EV3"},
                ],
                integration_rows=[
                    {"column_header": "INT1", "author_conclusion": True},
                    {"column_header": "INT2", "author_conclusion": True},
                ],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Author Conclusion Validation"))

    def test_tag_cross_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=[
                    {
                        "column_header": "EV1",
                        "source_tag": "source_missing",
                        "method_tag": "method_missing",
                    },
                    {"column_header": "EV2"},
                    {"column_header": "EV3"},
                ],
                integration_rows=[
                    {"column_header": "INT1", "author_conclusion": True, "method_tag": "method_missing2"},
                    {"column_header": "INT2", "author_conclusion": False},
                ],
                source_rows=[{"source_tag": "source_ok"}],
                method_rows=[{"method_tag": "method_ok"}],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Evidence - Tag Validation"))
            self.assertTrue(_has_step(results, "Integration - Tag Validation"))
