from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    confirmed: bool = False  # True when query is confirmed, frontend can hide input
    awaiting_confirmation: bool = False  # True when showing confirmation buttons


class ExtractedParams(BaseModel):
    """Parameters extracted from a single user message."""
    terms: list[str] | None = None  # Can be multiple: ["Fall 2024", "Fall 2025"]
    level: str | None = None  # Undergraduate, Graduate, All
    mode: str | None = None  # Campus Immersion, Digital Immersion, All
    metric: str | None = None  # Resident Status, Degree Level, STEM discipline, College, Campus
    variable: str | None = None  # Specific value within the metric
    is_confirmation: bool = False  # User confirmed with "yes", "correct", etc.
    wants_to_change: str | None = None  # If user wants to modify something


class ConversationState(BaseModel):
    """Accumulated state across the conversation."""
    terms: list[str] = []  # Supports multiple terms
    level: str | None = None
    mode: str | None = None
    metric: str | None = None
    variable: str | None = None
    confirmed: bool = False
    awaiting_confirmation: bool = False

    def get_missing_required(self) -> list[str]:
        """Return list of missing required fields."""
        missing = []
        if not self.terms:
            missing.append("term")
        if not self.level:
            missing.append("level")
        if not self.mode:
            missing.append("mode")
        return missing

    def is_complete(self) -> bool:
        """Check if all required fields are filled."""
        return len(self.get_missing_required()) == 0

    def merge_extracted(self, extracted: ExtractedParams, asking_for: str | None = None) -> "ConversationState":
        """
        Merge newly extracted params into state.

        Rules:
        - terms: Combine lists, don't overwrite
        - level, mode: Only fill if currently None, NEVER overwrite
        - metric, variable: Can be updated anytime
        """
        # For terms: combine with existing (allow adding more terms)
        new_terms = self.terms.copy()
        if extracted.terms:
            for t in extracted.terms:
                if t not in new_terms:
                    new_terms.append(t)

        # For required single fields: ONLY fill if currently empty
        new_level = self.level if self.level else extracted.level
        new_mode = self.mode if self.mode else extracted.mode

        # Special case: if we're asking for mode and got "All" as level
        if asking_for and extracted.level == "All" and extracted.mode is None:
            if asking_for == "mode" and not self.mode:
                new_mode = "All"
                new_level = self.level

        # For optional fields: allow updates
        new_metric = extracted.metric or self.metric
        new_variable = extracted.variable or self.variable

        return ConversationState(
            terms=new_terms,
            level=new_level,
            mode=new_mode,
            metric=new_metric,
            variable=new_variable,
            confirmed=self.confirmed,
            awaiting_confirmation=self.awaiting_confirmation,
        )

    def to_summary(self) -> str:
        """Generate a human-readable summary of the current state."""
        parts = []
        if self.terms:
            if len(self.terms) == 1:
                parts.append(f"**Term**: {self.terms[0]}")
            else:
                parts.append(f"**Terms**: {', '.join(self.terms)}")
        if self.level:
            parts.append(f"**Level**: {self.level}")
        if self.mode:
            parts.append(f"**Mode**: {self.mode}")
        if self.metric and self.variable:
            parts.append(f"**Focus**: {self.metric} → {self.variable}")
        elif self.metric:
            parts.append(f"**Category**: {self.metric}")
        elif self.variable:
            parts.append(f"**Focus**: {self.variable}")
        return "\n".join(parts) if parts else "No parameters collected yet."
