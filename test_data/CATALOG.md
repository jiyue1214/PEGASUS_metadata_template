# Test Data Catalog

This catalog lists TSV/XLSX fixtures in `test_data/` and the expected validation outcome.

## List validation
| Test| Validator | Expected outcome | Notes |
| --- | --- | --- | --- |
| success | list | success | Example list file with valid headers and rows. |
| missing_variant_id | list | error | Header validation error: missing `PrimaryVariantID`. |
| missing_genesymbol | list | error | Header validation error: missing `GeneSymbol`. |
| invalid_variantid | list | error | invalid `PrimaryVariantID`:chr1:100000:TM:C  |
| invalid_genesymbol | list | error | Invalidate value in the `GeneSymbol`. e.g. 1.0 |
| invalid_number_of_int| list | error | More than one "INT_" column |
| invalid_no_int| list | error | No "INT_" column in the list|
| invalid_no_evidence| list | error | Only integration result and no evidence|
| invalid_contains_other_column| list | warning | Unrecognised columns|
| invalid_value| list | error | Invaild value (not boolean)|
| invalid_more_than_one_list_in_dir| list | error | More than one lists in a folder|

## Matrix validation
| Test| Validator | Expected outcome | Notes |
| --- | --- | --- | --- |
| success | matrix | success | Example matrix file with valid headers and rows. |
| missing_variant_id | matrix | error | Header validation error: missing `PrimaryVariantID`. |
| missing_geneid | matrix | error | Header validation error: missing `GeneID`. |
| missing_genesymbol | matrix | error | Header validation error: missing `GeneSymbol`. |
| invalid_variantid | matrix| error | invalid `PrimaryVariantID`:chr1:100000:TM:C  |
| invalid_rsid | matrix | error | invalid `rsID`:1234 |
| invalid_genesymbol | matrix | error | Invalidate value in the `GeneSymbol`. e.g. 1.0 |
| invalid_locusrange | matrix | error | Invalidate value in the `LocusRange`. Z:12345|
| invalid_contains_other_column| matrix | warning | Unrecognised columns|
| invalid_one_evidence| matrix | error | there is only one evidence|
| invalid_no_int| matrix | error | No "INT_" column in the matrix|
| invalid_more_than_one_matrix_in_dir| matrix | error | More than one matrices in a folder|

## Metadata validation

## Cross validation