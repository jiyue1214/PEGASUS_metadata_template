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

def _empty_sheet_df(model: type) -> pd.DataFrame:
    base = _example_row(model)
    return pd.DataFrame(columns=base.keys())


def _write_metadata_excel(
    path: Path,
    evidence_rows: List[Dict[str, Any]],
    integration_rows: List[Dict[str, Any]],
    source_rows: Optional[List[Dict[str, Any]]] = None,
    method_rows: Optional[List[Dict[str, Any]]] = None,
    dataset_rows: Optional[List[Dict[str, Any]]] = None,
    genomic_rows: Optional[List[Dict[str, Any]]] = None,
    omit_sheets: Optional[List[str]] = None,
    drop_columns: Optional[Dict[str, List[str]]] = None,
) -> None:
    normalized_omit = {name.lower().strip() for name in (omit_sheets or [])}
    normalized_drop = {
        name.lower().strip(): cols for name, cols in (drop_columns or {}).items()
    }

    dataset_df = _build_sheet_df(DatasetDescription, dataset_rows or [{}])
    genomic_df = _build_sheet_df(GenomicIdentifier, genomic_rows or [{}])
    evidence_df = _build_sheet_df(Evidence, evidence_rows)
    integration_df = (
        _empty_sheet_df(Integration)
        if integration_rows == []
        else _build_sheet_df(Integration, integration_rows)
    )
    source_df = _build_sheet_df(Source, source_rows or [{}])
    method_df = _build_sheet_df(Method, method_rows or [{}])

    if normalized_drop.get("datasetdescription"):
        dataset_df = dataset_df.drop(columns=normalized_drop["datasetdescription"], errors="ignore")
    if normalized_drop.get("genomicidentifier"):
        genomic_df = genomic_df.drop(columns=normalized_drop["genomicidentifier"], errors="ignore")
    if normalized_drop.get("evidence"):
        evidence_df = evidence_df.drop(columns=normalized_drop["evidence"], errors="ignore")
    if normalized_drop.get("integration"):
        integration_df = integration_df.drop(columns=normalized_drop["integration"], errors="ignore")
    if normalized_drop.get("source"):
        source_df = source_df.drop(columns=normalized_drop["source"], errors="ignore")
    if normalized_drop.get("method"):
        method_df = method_df.drop(columns=normalized_drop["method"], errors="ignore")

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        if "datasetdescription" not in normalized_omit:
            dataset_df.to_excel(writer, sheet_name="DatasetDescription", index=False, startrow=1)
        if "genomicidentifier" not in normalized_omit:
            genomic_df.to_excel(writer, sheet_name="GenomicIdentifier", index=False, startrow=1)
        if "evidence" not in normalized_omit:
            evidence_df.to_excel(writer, sheet_name="Evidence", index=False, startrow=1)
        if "integration" not in normalized_omit:
            integration_df.to_excel(writer, sheet_name="Integration", index=False, startrow=1)
        if "source" not in normalized_omit:
            source_df.to_excel(writer, sheet_name="Source", index=False, startrow=1)
        if "method" not in normalized_omit:
            method_df.to_excel(writer, sheet_name="Method", index=False, startrow=1)


def _has_step(results: List[Dict[str, Any]], step: str) -> bool:
    return any(result.get("step") == step for result in results)

def _has_type(results: List[Dict[str, Any]], kind: str) -> bool:
    return any(result.get("type") == kind for result in results)

def _valid_evidence_rows(
    count: int,
    source_tag: str = "source_ok",
    method_tag: str = "method_ok",
) -> List[Dict[str, Any]]:
    return [
        {
            "column_header": f"EV{i}",
            "column_description": f"Evidence {i}",
            "evidence_category": "Molecular QTL",
            "evidence_category_abbreviation": "QTL",
            "variant_or_gene_centric": "variant-centric",
            "source_tag": source_tag,
            "method_tag": method_tag,
        }
        for i in range(1, count + 1)
    ]

def _valid_integration_rows(
    count: int,
    author_conclusion_index: int = 0,
    method_tag: str = "method_ok",
) -> List[Dict[str, Any]]:
    return [
        {
            "integration_tag": f"int{i}",
            "column_header": f"INT{i}",
            "column_description": f"Integration {i}",
            "author_conclusion": i - 1 == author_conclusion_index,
            "method_tag": method_tag,
        }
        for i in range(1, count + 1)
    ]


class TestMetadataValidation(unittest.TestCase):
    def test_evidence_requires_more_than_two_valid_rows(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(2),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Evidence - Row Count"))

    def test_integration_requires_more_than_one_valid_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(2, author_conclusion_index=1),
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Row Count"))

    def test_author_conclusion_requires_exactly_one_true(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            rows = _valid_integration_rows(3, author_conclusion_index=1)
            rows[2]["author_conclusion"] = True
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=rows,
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Author Conclusion"))

    def test_tag_cross_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4, source_tag="source_missing", method_tag="method_missing"),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1, method_tag="method_missing2"),
                source_rows=[{}, {"source_tag": "source_ok"}],
                method_rows=[{}, {"method_tag": "method_ok"}],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Evidence - Tag Reference"))
            self.assertTrue(_has_step(results, "Integration - Tag Reference"))

    def test_catalog_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                source_rows=[{}, {"source_tag": "source_ok"}],
                method_rows=[{}, {"method_tag": "method_ok"}],
                dataset_rows=[{}, {"trait_description": "Trait A"}],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertFalse(_has_type(results, "error"))

    def test_catalog_missing_essential_tab(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                omit_sheets=["DatasetDescription"],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Sheet Validation"))

    def test_catalog_missing_mandatory_columns_dataset(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                drop_columns={"DatasetDescription": ["trait_description"]},
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "DatasetDescription - Header Validation"))

    def test_catalog_missing_mandatory_columns_identifier(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                drop_columns={"GenomicIdentifier": ["genome_build"]},
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "GenomicIdentifier - Header Validation"))

    def test_catalog_missing_mandatory_columns_evidence(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                drop_columns={"Evidence": ["column_header"]},
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Evidence - Header Validation"))

    def test_catalog_missing_mandatory_columns_integration(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                drop_columns={"Integration": ["column_description"]},
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Header Validation"))

    def test_catalog_gwas_source_is_gwas_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            gwas_overrides = {
                "gwas_samples_description": None,
                "gwas_sample_size": None,
                "gwas_case_control_study": None,
                "gwas_sample_ancestry": None,
                "gwas_sample_ancestry_label": None,
            }
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                source_rows=[{}, {"source_tag": "source_ok"}],
                method_rows=[{}, {"method_tag": "method_ok"}],
                dataset_rows=[{}, {"gwas_source": "GCST123456", **gwas_overrides}],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertFalse(_has_type(results, "error"))

    def test_catalog_gwas_source_is_not_gwas_catalog(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            gwas_overrides = {
                "gwas_samples_description": None,
                "gwas_sample_size": None,
                "gwas_case_control_study": None,
                "gwas_sample_ancestry": None,
                "gwas_sample_ancestry_label": None,
            }
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                dataset_rows=[{}, {"gwas_source": "PMID:1234", **gwas_overrides}],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "DatasetDescription - Row Validation"))

    def test_catalog_evidence_category_not_in_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            rows = _valid_evidence_rows(4)
            rows[1]["evidence_category"] = "UNKNOWN"
            _write_metadata_excel(
                path,
                evidence_rows=rows,
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Evidence - Row Validation"))

    def test_catalog_evidence_category_only_one(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(2),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Evidence - Row Count"))

    def test_catalog_no_integration_row(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=[],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Row Count"))

    def test_catalog_more_than_one_author_conclusion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            rows = _valid_integration_rows(3, author_conclusion_index=1)
            rows[2]["author_conclusion"] = True
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=rows,
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Author Conclusion"))

    def test_catalog_no_author_conclusion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            rows = _valid_integration_rows(3, author_conclusion_index=2)
            rows[1]["author_conclusion"] = False
            rows[2]["author_conclusion"] = False
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=rows,
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Author Conclusion"))

    def test_catalog_evidence_category_miss_source_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4, source_tag="source_missing"),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1),
                source_rows=[{}, {"source_tag": "source_ok"}],
                method_rows=[{}, {"method_tag": "method_ok"}],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Evidence - Tag Reference"))

    def test_catalog_evidence_category_miss_method_tag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "meta.xlsx"
            _write_metadata_excel(
                path,
                evidence_rows=_valid_evidence_rows(4),
                integration_rows=_valid_integration_rows(3, author_conclusion_index=1, method_tag="method_missing"),
                source_rows=[{}, {"source_tag": "source_ok"}],
                method_rows=[{}, {"method_tag": "method_ok"}],
            )
            results = PegMetadataValidation(path).validate_metadata()
            self.assertTrue(_has_step(results, "Integration - Tag Reference"))
