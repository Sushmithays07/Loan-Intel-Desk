"""Pydantic models: request validation and response shapes."""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class LoanApplication(BaseModel):
    """Raw applicant inputs (the 13 non-engineered model features)."""
    model_config = ConfigDict(extra="forbid")

    age: int = Field(ge=18, le=100)
    annual_income: float = Field(gt=0, le=1e10, description="Must be > 0 (used as a divisor)")
    credit_score: int = Field(ge=300, le=900)
    loan_amount: float = Field(gt=0, le=1e10, description="Must be > 0 (used as a divisor)")
    loan_term: int = Field(ge=6, le=360, description="Months")
    existing_loans: int = Field(ge=0, le=50)
    existing_loan_amount: float = Field(ge=0, le=1e10)
    monthly_emi: float = Field(ge=0, le=1e9)
    dependents: int = Field(ge=0, le=20)
    savings: float = Field(ge=0, le=1e10)
    employment_years: int = Field(ge=0, le=60)
    previous_defaults: int = Field(ge=0, le=50)
    assets: float = Field(ge=0, le=1e11)


class Ratios(BaseModel):
    dti: float
    loan_income_ratio: float
    savings_loan_ratio: float


class StorageStatus(BaseModel):
    saved: bool
    message: str


class PredictionResponse(BaseModel):
    application_id: str
    created_at: datetime
    prediction: int
    prediction_label: str
    approval_probability: float
    rejection_probability: float
    ratios: Ratios
    model_features: dict[str, float]
    model_version: str
    storage: StorageStatus
    warnings: list[str] = []
    disclaimer: str


class HistoryItem(BaseModel):
    application_id: str
    created_at: str
    loan_amount: Optional[float] = None
    credit_score: Optional[int] = None
    loan_term: Optional[int] = None
    prediction_label: str
    approval_probability: float


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    page: int
    page_size: int
    total_pages: int
