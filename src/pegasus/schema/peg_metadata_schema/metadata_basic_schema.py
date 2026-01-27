from typing import  Literal, Optional
from pydantic import BaseModel, Field, HttpUrl
from pegasus.schema_defintation.control_verb import (
    Text, LongText, Identifier, ShortText,
    OntologyUnderscoreID,
    GCST,
    PMID,
    DOI,
    AncestryCategory,
    GenomeBuild,
)

# ----------------------------
# Sheet: Genomic_identifier
# ----------------------------

class DatasetDescription(BaseModel):
    """
    Descriptors for the whole PEG matrix (trait, source of the matrix itself, publication reference, release date, creator)
    """
    trait_description: ShortText = Field(
        ...,
        description="Free-text description of the phenotype under investigation.",
        json_schema_extra={"header": "trait_description", "example": "Ascorbic acid 3-sulfate levels"},
    )

    trait_ontology_id: Optional[OntologyUnderscoreID] = Field(
        default=None,
        description="Standard ontology identifier mapped to the trait (e.g., EFO, MONDO, HPO, DOID).",
        json_schema_extra={"header": "trait_ontology_id", "example": "EFO_0800173"},
    )

    gwas_source: Optional[GCST | PMID | HttpUrl | DOI] = Field(
        default=None,
        description="Identifier of the GWAS source. Prefer GWAS Catalog accession (GCST); if not available, use PubMed ID, doi, url",
        json_schema_extra={"header": "gwas_source", "example": "GCST000001"},
    )

    peg_source: Optional[GCST | PMID | HttpUrl | DOI] = Field(
        default=None,
        description="Identifier of the origin of the PEG list (e.g., publication, DOI, preprint, URL).",
        json_schema_extra={"header": "peg_source", "example": "PMID:36357675"},
    )

    gwas_samples_description: Optional[LongText] = Field(
        default=None,
        description="Detailed description of the GWAS samples.",
        json_schema_extra={"header": "gwas_samples_description", "example": "6,136 Finnish ancestry individuals"},
    )

    gwas_sample_size: Optional[int] = Field(
        default=None,
        description="Total number of individuals included in the GWAS analysis.",
        json_schema_extra={"header": "gwas_sample_size", "example": 6136},
    )

    gwas_case_control_study: Optional[bool] = Field(
        default=None,
        description="Indicator of whether the GWAS design is case–control (TRUE or FALSE).",
        json_schema_extra={"header": "gwas_case_control_study", "example": False},
    )

    gwas_sample_ancestry: Optional[Text] = Field(
        default=None,
        description="Free-text description of participant ancestry",
        json_schema_extra={"header": "gwas_sample_ancestry", "example": "Finland"},
    )

    gwas_sample_ancestry_label: Optional[AncestryCategory | ShortText] = Field(
        default=None,
        description="Broad ancestry category that best describes the sample. Multiple values can be listed separated by '|'.",
        json_schema_extra={"header": "gwas_sample_ancestry_label", "example": "European"},
    )

class GenomicIdentifier(BaseModel):
    """
    Details about the variants, genes, or locus included in your dataset.
    """

    variant_type: Optional[ShortText] = Field(
        default=None,
        description="Explanation of how the main variant was selected  (e.g., lead, sentinel, index, mixed).",
        json_schema_extra={"header": "variant_type", "example": "lead"},
    )

    genome_build: GenomeBuild = Field(
        default="GRCh38",
        description="Genome assembly used to map variants.",
        json_schema_extra={"header": "genome_build", "example": "GRCh38"},
    )

    variant_information: Optional[LongText] = Field(
        default=None,
        description="Additional free-text notes about the variant",
        json_schema_extra={"header": "variant_information", "example": "The primary variant is the variant with the most significant association p-value in the study"},
    )
    gene_id_source_version: Optional[Identifier] = Field(
        default=None,
        description="Version of the source database used for gene symbols/IDs (e.g., HGNC version).",
        json_schema_extra={"header": "gene_id_source_version", "example": "Ensembl v109"},
    )
    gene_symbol_source_version: Optional[Identifier] = Field(
        default=None,
        description="Version of the gene symbol reference authority",
        json_schema_extra={"header": "gene_symbol_source_version", "example": "HGNC 2025-07-30"},
    )
    info: Optional[LongText] = Field(
        default=None,
        description="Additional gene-level metadata that supports interpretation.",
        json_schema_extra={"header": "info", "example": "NA"},
    )
    locus_type: Optional[ShortText] = Field(
        default=None,
        description="Method used to define locus boundaries",
        json_schema_extra={"header": "locus_type", "example": "lead_variant +/- 500kb"},
    )
    locus_id: Optional[Identifier] = Field(
        default=None,
        description="Provide the explanation of how the identifier was derived",
        json_schema_extra={"header": "locus_id", "example": "lead_variant"},
    )
    locus_info: Optional[LongText] = Field(
        default=None,
        description="Additional information supporting locus interpretation.",
        json_schema_extra={"header": "locus_info", "example": "Locus information"},
    )