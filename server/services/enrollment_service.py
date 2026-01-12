from datetime import datetime
from pathlib import Path

import pandas as pd
from pydantic import BaseModel

from brain.utils.logger import logger


# Path to Excel file (relative to server directory, then up to parent)
EXCEL_FILE_PATH = Path(__file__).parent.parent.parent / "enrollment_trends.xlsx"


class EnrollmentQueryResult(BaseModel):
    """Single row result from enrollment query."""

    term: str
    student_count: int
    description: str
    metric: str | None = None
    variable: str | None = None


class EnrollmentQueryResponse(BaseModel):
    """Complete response from enrollment query."""

    results: list[EnrollmentQueryResult]
    query_summary: str
    total_across_terms: int | None = None


class EnrollmentDataService:
    """
    Service for loading and querying enrollment data with caching.

    Uses singleton pattern to ensure DataFrame is loaded once and cached.
    """

    _instance: "EnrollmentDataService | None" = None
    _df: pd.DataFrame | None = None
    _last_loaded: datetime | None = None
    CACHE_TTL_SECONDS: int = 3600  # 1 hour cache

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "EnrollmentDataService":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _should_reload(self) -> bool:
        """Check if cache has expired."""
        if self._df is None or self._last_loaded is None:
            return True
        elapsed = (datetime.now() - self._last_loaded).total_seconds()
        return elapsed > self.CACHE_TTL_SECONDS

    def _load_data(self) -> pd.DataFrame:
        """Load Excel file with caching."""
        if not self._should_reload():
            logger.info("Using cached enrollment data")
            return self._df

        logger.info(f"Loading enrollment data from {EXCEL_FILE_PATH}")

        if not EXCEL_FILE_PATH.exists():
            raise FileNotFoundError(f"Excel file not found: {EXCEL_FILE_PATH}")

        self._df = pd.read_excel(EXCEL_FILE_PATH)
        self._last_loaded = datetime.now()
        logger.info(f"Loaded {len(self._df)} rows from enrollment data")
        return self._df

    def query(
        self,
        terms: list[str],
        level: str,
        mode: str,
        metric: str | None = None,
        variable: str | None = None,
    ) -> EnrollmentQueryResponse:
        """
        Query enrollment data based on parameters.

        Args:
            terms: List of terms (e.g., ["Fall 2024", "Fall 2025"])
            level: "Undergraduate", "Graduate", or "All"
            mode: "Campus Immersion", "Digital Immersion", or "All"
            metric: Optional metric filter (e.g., "STEM discipline")
            variable: Optional variable filter (e.g., "STEM")

        Returns:
            EnrollmentQueryResponse with results for each term
        """
        df = self._load_data()

        logger.info(
            f"Querying: terms={terms}, level={level}, mode={mode}, "
            f"metric={metric}, variable={variable}"
        )

        # Start with base filters
        mask = (
            (df["Term"].isin(terms))
            & (df["Undergraduate or Graduate"] == level)
            & (df["Campus or Digital"] == mode)
        )

        # Apply metric/variable filters based on what's specified
        if metric and variable:
            # Specific metric and variable requested
            mask &= (df["Metric"] == metric) & (df["Variable"] == variable)
        elif metric:
            # Metric specified but no variable - return all variables for that metric
            mask &= df["Metric"] == metric
        else:
            # No metric/variable - return only "All" rows (total count)
            # "All" in Variable column with "Campus" Metric gives total enrollment
            mask &= (df["Variable"] == "All") & (df["Metric"] == "Campus")

        filtered_df = df[mask]
        logger.info(f"Query returned {len(filtered_df)} rows")

        # Build results
        results = []
        for _, row in filtered_df.iterrows():
            results.append(
                EnrollmentQueryResult(
                    term=row["Term"],
                    student_count=int(row["Number of students"]),
                    description=row["Description"],
                    metric=row["Metric"] if metric else None,
                    variable=row["Variable"] if (metric or variable) else None,
                )
            )

        # Sort by term (chronological order)
        results.sort(key=lambda x: x.term)

        # Calculate total if multiple terms
        total = None
        if len(terms) > 1 and results:
            total = sum(r.student_count for r in results)

        # Generate query summary
        summary_parts = [
            f"Terms: {', '.join(terms)}",
            f"Level: {level}",
            f"Mode: {mode}",
        ]
        if metric:
            summary_parts.append(f"Metric: {metric}")
        if variable:
            summary_parts.append(f"Variable: {variable}")

        return EnrollmentQueryResponse(
            results=results,
            query_summary=" | ".join(summary_parts),
            total_across_terms=total,
        )
