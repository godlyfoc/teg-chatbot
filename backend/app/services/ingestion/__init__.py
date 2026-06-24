"""Full ingestion pipeline with change detection."""

from app.services.ingestion.pipeline import run_ingestion

__all__ = ["run_ingestion"]
