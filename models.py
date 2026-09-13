from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class DoujiaRecord(BaseModel):
    song: str
    account: str
    doujia_amount: int = Field(ge=0)
    doujia_payer: str | None = None
    source_line: str


class AdvanceRecord(BaseModel):
    account: str
    advance_amount: int = Field(ge=0)
    song: str
    payer: str | None = None
    expected_payment_date: date | None = None
    source_line: str


class Issue(BaseModel):
    code: Literal[
        "declared_count_mismatch",
        "declared_total_mismatch",
        "missing_field",
        "date_anomaly",
        "duplicate_application",
        "unmatched_account",
    ]
    severity: Literal["warning", "manual_review"] = "manual_review"
    message: str
    source: str
    accounts: list[str] = Field(default_factory=list)


class ProcessingResult(BaseModel):
    doujia_date: date | None = None
    doujia_declared_total: int | None = None
    doujia_records: list[DoujiaRecord] = Field(default_factory=list)
    advance_date: date | None = None
    advance_declared_total: int | None = None
    advance_declared_count: int | None = None
    advance_records: list[AdvanceRecord] = Field(default_factory=list)
    issues: list[Issue] = Field(default_factory=list)
    totals: dict[str, int] = Field(default_factory=dict)
