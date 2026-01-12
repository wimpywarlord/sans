import uuid
from fastapi import APIRouter, HTTPException

from schemas.chat import ChatRequest, ChatResponse, ConversationState
from services.llm_service import extract_params, generate_response, generate_data_response
from services.enrollment_service import EnrollmentDataService
from brain.utils.logger import logger

router = APIRouter(prefix="/chat", tags=["chat"])

# In-memory conversation state storage
# Key: conversation_id, Value: (ConversationState, asking_for)
conversation_data: dict[str, tuple[ConversationState, str | None]] = {}


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Process a chat message using 2-stage LLM approach:
    1. Extract parameters from user message (with context about what we asked)
    2. Merge with existing state (protecting already-filled fields)
    3. Generate appropriate response
    """
    conversation_id = request.conversation_id or str(uuid.uuid4())
    is_new_conversation = conversation_id not in conversation_data

    logger.info(f"Chat request - conversation_id: {conversation_id}, message: {request.message[:50]}...")

    # Get or create conversation state
    if is_new_conversation:
        state = ConversationState()
        asking_for = None
        logger.info(f"New conversation started: {conversation_id}")
    else:
        state, asking_for = conversation_data[conversation_id]

    logger.info(f"Current state: {state}, asking_for: {asking_for}")

    try:
        # Stage 1: Extract parameters WITH context about what we were asking
        extracted = extract_params(request.message, asking_for=asking_for)
        logger.info(f"Extracted: {extracted}")

        # Handle confirmation
        if extracted.is_confirmation and state.awaiting_confirmation:
            state.confirmed = True
            state.awaiting_confirmation = False
            logger.info("User confirmed the query")

        # Handle change request
        if extracted.wants_to_change:
            change_field = extracted.wants_to_change.lower()
            if "term" in change_field:
                state.terms = []  # Clear terms list
            elif "level" in change_field or "grad" in change_field:
                state.level = None
            elif "mode" in change_field or "campus" in change_field or "digital" in change_field:
                state.mode = None
            state.awaiting_confirmation = False
            state.confirmed = False
            logger.info(f"User wants to change: {extracted.wants_to_change}")

        # Merge extracted params (with asking_for context for smart handling)
        state = state.merge_extracted(extracted, asking_for=asking_for)

        # Check if ready for confirmation
        if state.is_complete() and not state.confirmed and not state.awaiting_confirmation:
            state.awaiting_confirmation = True
            logger.info("All required fields collected, awaiting confirmation")

        # Determine what we're asking for NEXT (for the next extraction)
        missing = state.get_missing_required()
        if state.awaiting_confirmation:
            next_asking_for = "confirmation"
        elif missing and not state.confirmed:
            next_asking_for = missing[0]
        else:
            next_asking_for = None

        # Save state + what we're asking for
        conversation_data[conversation_id] = (state, next_asking_for)
        logger.info(f"Updated state: {state}, next_asking_for: {next_asking_for}")

        # Stage 2: Generate response
        if state.confirmed:
            # Query enrollment data and generate data-driven response
            logger.info("Querying enrollment data for confirmed query")
            service = EnrollmentDataService.get_instance()
            query_results = service.query(
                terms=state.terms,
                level=state.level,
                mode=state.mode,
                metric=state.metric,
                variable=state.variable,
            )
            logger.info(f"Query returned {len(query_results.results)} results")
            response_text = generate_data_response(state, query_results)
        else:
            # Generate conversational response for parameter collection
            response_text = generate_response(
                state=state,
                user_message=request.message,
                is_first_message=is_new_conversation,
            )

        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            confirmed=state.confirmed,
            awaiting_confirmation=state.awaiting_confirmation,
        )

    except Exception as e:
        logger.error(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@router.get("/{conversation_id}/state")
async def get_state(conversation_id: str):
    """Get the current state of a conversation (for debugging)."""
    if conversation_id in conversation_data:
        state, asking_for = conversation_data[conversation_id]
        return {
            "conversation_id": conversation_id,
            "state": state.model_dump(),
            "asking_for": asking_for,
            "missing": state.get_missing_required(),
            "is_complete": state.is_complete(),
        }
    raise HTTPException(status_code=404, detail="Conversation not found")


@router.delete("/{conversation_id}")
async def clear_conversation(conversation_id: str):
    """Clear a conversation's state."""
    if conversation_id in conversation_data:
        del conversation_data[conversation_id]
        logger.info(f"Conversation cleared: {conversation_id}")
        return {"message": "Conversation cleared"}
    raise HTTPException(status_code=404, detail="Conversation not found")
