# Repo plan (schema + validation)
## Validation rules (current behavior)
### Common header conventions
- Evidence columns are detected by prefix:
  - The part before the first `_` must match a valid evidence category name from `core.py`.
- Integration columns must start with `INT_`.
- “Other identifiers” are any headers starting with `Var_`, `Gene_`, or `Locus_`.

### PEG matrix (`matrix_validation.py`)
Header checks:
- All headers must be recognized; unrecognized columns trigger a warning and stop validation.
- At least **one** `INT_` column is required.
- At least **two** evidence columns are required.

Fixed-column checks (Pandera, `MatrixIdentifiesPandera`):
- `PrimaryVariantID`: required, `chr<1-22|X|Y|M|MT>:pos:REF:ALT` regex.
- `rsID`: optional, `rs<digits>` regex.
- `GeneID`: required (no regex; must be non-null string).
- `GeneSymbol`: required, must be a real Python `str` and **not purely numeric**.
- `LocusRange`: optional, `chr<1-22|X|Y|M|MT>:start-end` regex.
- `Locus_ID`: optional (no regex).

Validation strategy:
- Fixed columns are validated in chunks (first 50k rows, then remaining).
- Errors are grouped by column and check, with row numbers and sample values.

## PEG metadata (`metadata_validation.py`)
Sheet handling:
- Reads Excel sheets with header row at row 2; skips the example row.
- Required sheets: DatasetDescription, GenomicIdentifier, Evidence, Integration, Source, Method.
- Unknown columns produce warnings; missing required columns are errors.
- String-typed fields accept numeric cell values (coerced to strings).

DatasetDescription conditional rule:
- If `gwas_source` is GCST*, then other GWAS fields remain optional.
- If `gwas_source` is present and not GCST*, the following become required:
  - `gwas_samples_description`
  - `gwas_sample_size`
  - `gwas_case_control_study`
  - `gwas_sample_ancestry`
  - `gwas_sample_ancestry_label`

Evidence sheet rules:
- Prefilled Evidence rows are ignored when `evidence_category` is 0 or 0.0.
- `evidence_category_abbreviation` must map to `evidence_category` per `EVIDENCE_CATEGORY_MAP`.

Cross-sheet rules:
- Evidence must have >2 validated rows.
- Integration must have >1 validated row.
- Exactly one Integration row must have `author_conclusion = TRUE`.
- Every `source_tag` referenced in Evidence must exist in Source.
- Every `method_tag` referenced in Evidence or Integration must exist in Method.

### PEG list (`list_validation.py`)
Header checks:
- Required identifier columns must be present (from `ListIdentifiers`):
  - `PrimaryVariantID` (alias: `primary_variant_id`, `rsID`)
  - `GeneSymbol` (alias: `gene_symbol`, `Gene symbol`)
- At least **one** `INT_` column is required.
- At least **one** evidence column is required.
- Unrecognized columns are allowed but reported as warnings and skipped in row validation.

Row checks (Pydantic, `PegListSchema` + `ListIdentifiers`):
- `PrimaryVariantID`: must match `chr:pos:ref:alt` regex (note: error text mentions rsID, but current validator only accepts chr-formatted IDs).
- `GeneSymbol`: must be a non-numeric string.
- Evidence columns: values must parse to **boolean** (`TRUE`/`FALSE` or actual bool).
- Integration columns: accepted as strings (no strict validation yet).

## Notes / gaps to address later
- Metadata validator is wired and enforces per-sheet + cross-sheet rules.
- Matrix header validation currently stops on any unknown header (warning + early return).
- PEG list PrimaryVariantID validator only accepts chr:pos:ref:alt even though message mentions rsID.

## Where the schema lives
- `src/pegasus/schema/core.py`
  - Shared Pydantic types and enums (IDs, ontology patterns, controlled vocabularies).
  - Evidence categories are defined here via enums:
    - `VariantEvidenceCategory`, `GeneEvidenceCategory`, `AnyEvidenceCategory`.
- `src/pegasus/schema/peg_matrix_schem.py`
  - **PEG matrix** fixed-column schema.
  - Pydantic model (`MatrixIdentifiesPydantic`) for docs/field definitions.
  - Pandera model (`MatrixIdentifiesPandera`) for table validation.
- `src/pegasus/schema/peg_list_schema.py`
  - **PEG list** schema using Pydantic (`PegListSchema`, `ListIdentifiers`).
- `src/pegasus/schema/constant.py`
  - Derived constants used for validation:
    - `evidence_category` (all evidence enum names)
    - `matrix_identifier_keys` / `list_identifier_keys`
    - `other_genetic_identifiers` prefixes (`Var_`, `Gene_`, `Locus_`)
- `src/pegasus/schema/peg_metadata_schema/`
  - Metadata sheet schemas (Pydantic) for dataset-level context.
  - Files include `metadata_basic_schema.py`, `metadata_method_schema.py`, etc.

## Where validation lives
- `src/pegasus/validation/matrix_validation.py`
  - PEG **matrix** TSV validation using Pandera + header rules.
- `src/pegasus/validation/list_validation.py`
  - PEG **list** TSV validation using Pydantic + header rules.
- `src/pegasus/validation/metadata_validation.py`
  - PEG **metadata** XLSX validation using Pydantic row checks plus cross-sheet rules.

## Why Pandera for PEG Matrix while Pydantic for PEG List
- PEG matrix is large, tabular, and contains fixed-column; Pandera is optimized for DataFrame validation and can validate in chunks for scale.
- PEG list is smaller and more flexible (dynamic evidence/int columns); Pydantic models are simpler to apply row-by-row with custom alias handling.
- The matrix uses Pandera for strict column-level checks, while the list uses Pydantic to validate structured dicts after header classification.
- Reference: # Reference:https://www.union.ai/blog-post/pandera-0-17-adds-support-for-pydantic-v
