import os
import json
from openai import OpenAI
from dotenv import load_dotenv
from brain.utils.logger import logger
from schemas.chat import ExtractedParams, ConversationState
from services.enrollment_service import EnrollmentQueryResponse

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Valid values for reference
VALID_TERMS = [f"Fall {year}" for year in range(2012, 2026)]
VALID_LEVELS = ["All", "Undergraduate", "Graduate"]
VALID_MODES = ["All", "Campus Immersion", "Digital Immersion"]
VALID_METRICS = ["Resident Status", "Degree Level", "STEM discipline", "College", "Campus"]


def get_extraction_prompt(asking_for: str | None = None) -> str:
    """Generate extraction prompt, optionally with context about what we're asking for."""

    context_hint = ""
    if asking_for == "term":
        context_hint = "\nCONTEXT: We just asked the user for TERM(s). They may specify one or multiple semesters."
    elif asking_for == "level":
        context_hint = "\nCONTEXT: We just asked for LEVEL. Short responses like 'all', 'grad', 'undergrad' refer to level."
    elif asking_for == "mode":
        context_hint = "\nCONTEXT: We just asked for MODE. Short responses like 'all', 'both', 'campus', 'online' refer to mode."
    elif asking_for == "confirmation":
        context_hint = "\nCONTEXT: We just asked the user to CONFIRM their query. Any affirmative response means is_confirmation: true."

    return f"""You are a parameter extractor for ASU enrollment data queries.

Extract parameters from the user message. Return ONLY valid JSON:

{{
  "terms": [array of strings] or null,  // e.g., ["Fall 2024"] or ["Fall 2024", "Fall 2025"]
  "level": string or null,
  "mode": string or null,
  "metric": string or null,
  "variable": string or null,
  "is_confirmation": boolean,
  "wants_to_change": string or null
}}
{context_hint}

Valid values:
- terms: Fall 2012 through Fall 2025 (can be multiple!)
- level: "Undergraduate", "Graduate", "All"
- mode: "Campus Immersion", "Digital Immersion", "All"
- metric: "Resident Status", "Degree Level", "STEM discipline", "College", "Campus"

Inference rules:
- "fall 24 and fall 25" → terms: ["Fall 2024", "Fall 2025"]
- "2024 and 2025" → terms: ["Fall 2024", "Fall 2025"]
- "last 3 years" → terms: ["Fall 2023", "Fall 2024", "Fall 2025"]
- "grad", "graduate" → level: "Graduate"
- "online", "digital" → mode: "Digital Immersion"
- "both" (for mode) → mode: "All"
- "yes", "ok", "okay", "sure", "correct", "confirm", "looks good", "that's right", "yep", "yup" → is_confirmation: true

METRIC/VARIABLE REFERENCE (use exact values):

1. metric: "STEM discipline"
   - variable: "STEM" (for STEM students)
   - variable: "Non-STEM"

2. metric: "Resident Status"
   - variable: "Resident" (in-state)
   - variable: "Non-Resident" (out-of-state)

3. metric: "Degree Level"
   - variable: "Associate", "Bachelor", "Master", "Doctor", "Law", "Non-Degree"

4. metric: "College"
   - variable: "Business", "Engineering", "Law", "Nursing and Health Innovation",
     "Liberal Arts and Sciences", "Design and the Arts", "Journalism", "Graduate College",
     "Health Solutions", "Global Futures", "Global Management", "New College", etc.

5. metric: "Campus"
   - variable: "Tempe", "Downtown Phoenix", "Polytechnic", "West Valley", "Other Locations"

INFERENCE EXAMPLES:
- "STEM students" → metric: "STEM discipline", variable: "STEM"
- "business students" → metric: "College", variable: "Business"
- "Tempe campus" → metric: "Campus", variable: "Tempe"
- "master's students" → metric: "Degree Level", variable: "Master"
- "in-state students" → metric: "Resident Status", variable: "Resident"

Handle typos. Return ONLY JSON."""


def extract_params(user_message: str, asking_for: str | None = None) -> ExtractedParams:
    """Extract parameters from a user message using LLM."""
    logger.info(f"Extracting params from: {user_message[:50]}... (context: asking_for={asking_for})")

    prompt = get_extraction_prompt(asking_for)

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0,
        max_tokens=200,
    )

    raw_response = response.choices[0].message.content.strip()
    logger.info(f"Extraction raw response: {raw_response}")

    try:
        data = json.loads(raw_response)

        # Handle terms as array
        terms = data.get("terms")
        if terms and not isinstance(terms, list):
            terms = [terms]  # Convert single string to list

        extracted = ExtractedParams(
            terms=terms,
            level=data.get("level"),
            mode=data.get("mode"),
            metric=data.get("metric"),
            variable=data.get("variable"),
            is_confirmation=data.get("is_confirmation", False),
            wants_to_change=data.get("wants_to_change"),
        )
        logger.info(f"Extracted params: {extracted}")
        return extracted
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse extraction response: {e}")
        return ExtractedParams()


def generate_response(
    state: ConversationState,
    user_message: str,
    is_first_message: bool = False,
) -> str:
    """Generate a conversational response based on current state."""
    missing = state.get_missing_required()
    is_complete = state.is_complete()
    state_summary = state.to_summary()

    if state.confirmed:
        # This case is now handled by generate_data_response, but keep as fallback
        return f"Your query is confirmed!\n\n{state_summary}"

    elif is_complete:
        # All fields collected - show structured confirmation (no LLM needed)
        return f"""I'll search for:

{state_summary}

Does this look correct?"""

    elif state.awaiting_confirmation:
        # User wants to change something (field was cleared, so is_complete is False)
        context = f"""User wants to make changes to their query.

Current state:
{state_summary}

Ask which field they want to change: Term, Level, or Mode?
Keep it SHORT. No greetings."""

    else:
        next_field = missing[0] if missing else None

        collected = []
        if state.terms:
            terms_str = ", ".join(state.terms)
            collected.append(f"Terms: {terms_str}")
        if state.level:
            collected.append(f"Level: {state.level}")
        if state.mode:
            collected.append(f"Mode: {state.mode}")
        if state.metric and state.variable:
            collected.append(f"Focus: {state.variable} ({state.metric})")

        collected_str = ", ".join(collected) if collected else "nothing yet"

        prompts = {
            "term": "Which semester(s)? (Fall 2012 - Fall 2025, can specify multiple)",
            "level": "Undergraduate, Graduate, or All?",
            "mode": "Campus Immersion, Digital Immersion, or All?",
        }

        if is_first_message:
            context = f"""User's first message: "{user_message}"

Extracted: {collected_str}
Still need: {next_field}

Briefly acknowledge what was understood, then ask for {next_field}.
Example: "Got it, [what they asked]. {prompts.get(next_field, '')}"
1-2 sentences. Direct."""
        else:
            context = f"""User said: "{user_message}"

Collected: {collected_str}
Need: {next_field}

Acknowledge briefly, then ask: {prompts.get(next_field, '')}
ONE short sentence. No greetings."""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are a concise ASU enrollment assistant. Never say 'Hi there'. Be direct."},
            {"role": "user", "content": context}
        ],
        temperature=0.7,
        max_tokens=200,
    )

    result = response.choices[0].message.content.strip()
    logger.info(f"Generated response: {result[:100]}...")
    return result


def generate_data_response(
    state: ConversationState,
    query_results: EnrollmentQueryResponse,
) -> str:
    """Generate a natural language response presenting query results."""
    logger.info(f"Generating data response for {len(query_results.results)} results")

    if not query_results.results:
        return (
            "I couldn't find any enrollment data matching your query. "
            "Please try different parameters or start a new conversation."
        )

    # Build results text for LLM context
    results_text = []
    for r in query_results.results:
        line = f"- {r.term}: {r.student_count:,} students"
        if r.variable:
            line += f" ({r.variable})"
        results_text.append(line)

    context = f"""Present these ASU enrollment results naturally:

Query: {query_results.query_summary}

Results:
{chr(10).join(results_text)}
"""

    if query_results.total_across_terms:
        context += f"\nTotal across all terms: {query_results.total_across_terms:,} students"

    context += """

Instructions:
- Present the data in ONE clear sentence
- Format numbers with commas (e.g., 45,230)
- For multiple terms, list each term's data on its own line
- Do NOT add commentary, analysis, or observations about trends
- Do NOT ask follow-up questions like "Is there anything else?"
- Do NOT say "Based on the data" or "According to"
- Just state the facts directly and concisely
- Example good response: "In Fall 2024, ASU had 14,368 graduate students in Campus Immersion programs."
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": "You are a concise ASU enrollment data assistant. State facts only. No commentary or follow-up questions.",
            },
            {"role": "user", "content": context},
        ],
        temperature=0.3,
        max_tokens=150,
    )

    result = response.choices[0].message.content.strip()
    logger.info(f"Generated data response: {result[:100]}...")
    return result
