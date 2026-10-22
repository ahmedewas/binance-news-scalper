"""Pydantic schemas for authenticated dashboard API."""
from pydantic import BaseModel, Field


class ActiveRequest(BaseModel):
    active: bool


class CloseRequest(BaseModel):
    symbol: str = Field(min_length=3, max_length=30, pattern=r"^[A-Z0-9]+/USDT$")


class ResetRequest(BaseModel):
    confirmation: str


class ModeRequest(BaseModel):
    mode: str = Field(pattern="^(PAPER|LIVE)$")
