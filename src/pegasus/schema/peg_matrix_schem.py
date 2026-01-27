from __future__ import annotations
from typing import Optional
import re
import pandera as pa
from pandera.typing import Series
from pydantic import BaseModel, Field

class MatrixIdentifiesPydantic(BaseModel):
    PrimaryVariantID: str = Field(
        ...,
        description="The variant to which variant-centric evidence relates. Used as the primary row ID; may be a lead variant, a variant in LD, or a fine-mapped SNP (defined in metadata).",
        examples=["chr10:114754071:T:C"],
        pattern=r"^chr(?:[1-9]|1[0-9]|2[0-2]|X|Y|M|MT):[1-9]\d*:[ATGC]+:[ATGC]+$",
    )
    rsID: Optional[str] = Field(
        None, 
        description="rsID of the primary variant.",
        examples=["rs1234"],
        pattern=r"^rs\d+$",
    )
    GeneID: str = Field(
        ..., 
        description="The gene under consideration in this row (gene-centric evidence). Primary identifier must be the Ensembl Gene ID. Other IDs can be added using GENE_[xyz] (e.g. GENE_EntrezID).",
        examples=["ENSG00000151532"]
        )
    GeneSymbol: str = Field(
        ..., 
        description="The gene under consideration in this row. Primary symbol must be the HGNC-approved gene symbol. Alternative/legacy symbols may be provided via GENE_[xyz] (e.g. GENE_alias).", 
        examples=["VTI1A"]
        )
    LocusRange: Optional[str] = Field(
        None, 
        description="The genomic range around the primary variant considered in this analysis.",
        examples=["chr10:114700000-114800000"],
        pattern=r"^chr(?:[1-9]|1[0-9]|2[0-2]|X|Y|M|MT):[1-9]\d*-[1-9]\d*$"
    )
    Locus_ID: Optional[str] = Field(
        None, 
        description="Internal or curated region ID. Recommended to use the associated variant (chr:bp or rsID); internal IDs may also be “Locus 1, Locus 2”.",
        examples=["chr10:114754071:T:C"]
    )


class MatrixIdentifiesPandera(pa.SchemaModel):
    PrimaryVariantID: Series[str] = pa.Field(
        nullable=False,
        str_matches=r"^chr(?:[1-9]|1[0-9]|2[0-2]|X|Y|M|MT):[1-9]\d*:[ATGC]+:[ATGC]+$",
        description="Expected chr:pos:ref:alt (e.g., chr10:114754071:T:C).",
    )
    rsID: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^rs\d+$",
        description="Expected rs followed by digits (e.g., rs1234).",
    )
    GeneID: Series[str] = pa.Field(nullable=False)
    GeneSymbol: Series[str] = pa.Field(nullable=False,
                                       coerce=False)
    
    @pa.check("GeneSymbol", name="strict_python_str", element_wise=True)
    def gene_symbol_is_str(cls, value: object) -> bool:
        # True only when the underlying Python type is exactly `str`
        return isinstance(value, str)

    @pa.check("GeneSymbol", name="non_numeric_symbol", element_wise=True)
    def gene_symbol_not_numeric(cls, value: object) -> bool:
        if not isinstance(value, str):
            return False
        stripped = value.strip()
        return re.fullmatch(r"[+-]?\d+(?:\.\d+)?", stripped) is None

    LocusRange: Series[str] = pa.Field(
        nullable=True,
        str_matches=r"^chr(?:[1-9]|1[0-9]|2[0-2]|X|Y|M|MT):[1-9]\d*-[1-9]\d*$",
        description="Expected chr#:start-end (e.g., chr10:114700000-114800000).",
    )
    Locus_ID: Series[str] = pa.Field(nullable=True)

    class Config:
        strict = True
