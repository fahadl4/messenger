
import os
import re
import calendar
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
from groq import AsyncGroq
from pydantic import BaseModel


load_dotenv()

api_key = os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("GROQ_API_KEY was not found in .env")

client = AsyncGroq(api_key=api_key)

PAKISTAN_TZ = ZoneInfo("Asia/Karachi")

VALID_RESPONSES = {"agreed", "declined", "unknown"}


# --------------------------------------------------
# Pydantic models
# --------------------------------------------------

class ParticipantResponse(BaseModel):
    user_id: int
    name: str
    response: str


class MeetingParticipant(BaseModel):
    user_id: int
    name: str


class MeetingDetails(BaseModel):
    meeting_agreed: bool
    title: str | None
    date: str | None
    weekday: str | None
    time: str | None
    duration_minutes: int | None
    participants: list[MeetingParticipant]
    participant_responses: list[ParticipantResponse]
    proposed_by_user_id: int | None = None
    needs_clarification: bool
    clarification_question: str | None


# --------------------------------------------------
# Make the JSON schema compatible with Groq strict mode
# --------------------------------------------------

def make_groq_compatible_schema(schema: dict) -> dict:
    if isinstance(schema, list):
        return [
            make_groq_compatible_schema(item)
            for item in schema
        ]

    if isinstance(schema, dict):
        schema = {
            key: make_groq_compatible_schema(value)
            for key, value in schema.items()
            if key != "default"
        }

        if schema.get("type") == "object":
            properties = schema.get("properties", {})
            schema["required"] = list(properties.keys())
            schema["additionalProperties"] = False

    return schema


# --------------------------------------------------
# Meeting date and time validation
# --------------------------------------------------

def validate_meeting_datetime(
    date_value: str | None,
    time_value: str | None,
    weekday_value: str | None,
    conversation: str,
) -> tuple[str | None, str | None]:
    """
    Validate the AI's meeting date and time.

    - Uses Pakistan time.
    - Calculates the next occurrence of a weekday when needed.
    - Corrects a weekday/date mismatch only when the conversation
      does not contain an explicit calendar date.
    - Rejects an explicitly dated meeting that is in the past.
    - Allows an unknown date or time to remain None.
    """

    now = datetime.now(PAKISTAN_TZ)
    today = now.date()

    # Determine the weekday from the AI response or conversation.
    weekday = None

    weekday_names = {
        name.casefold(): index
        for index, name in enumerate(calendar.day_name)
    }

    if weekday_value:
        weekday = weekday_names.get(weekday_value.strip().casefold())

        if weekday is None:
            raise ValueError(
                f"Invalid weekday returned by AI: {weekday_value}"
            )

    # If the AI omitted the weekday, try to identify one mentioned
    # in the conversation.
    if weekday is None:
        weekday_pattern = re.compile(
            r"\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
            re.IGNORECASE,
        )

        matches = weekday_pattern.findall(conversation)

        # Use the weekday only when exactly one distinct weekday
        # is mentioned. Multiple weekdays may indicate ambiguity.
        distinct_weekdays = {
            match.casefold() for match in matches
        }

        if len(distinct_weekdays) == 1:
            weekday_name = next(iter(distinct_weekdays))
            weekday = weekday_names[weekday_name]

    # Detect explicit calendar dates in the conversation.
    # A weekday such as "Sunday" by itself is not an explicit date.
    explicit_date_pattern = re.compile(
        r"\b\d{4}-\d{1,2}-\d{1,2}\b"
        r"|\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b"
        r"|\b\d{1,2}\s+(?:January|February|March|April|May|June|"
        r"July|August|September|October|November|December)"
        r"(?:\s+\d{4})?\b"
        r"|\b(?:January|February|March|April|May|June|July|August|"
        r"September|October|November|December)\s+\d{1,2}"
        r"(?:,?\s+\d{4})?\b",
        re.IGNORECASE,
    )

    explicit_date = bool(
        explicit_date_pattern.search(conversation)
    )

    # Validate the AI's date, if supplied.
    meeting_date = None

    if date_value:
        try:
            meeting_date = date.fromisoformat(date_value)
        except ValueError as exc:
            raise ValueError(
                "AI returned an invalid calendar date."
            ) from exc

        if meeting_date.isoformat() != date_value:
            raise ValueError(
                "Meeting date must use YYYY-MM-DD format."
            )

    # Validate the AI's time, if supplied.
    meeting_time = None

    if time_value:
        try:
            meeting_time = time.fromisoformat(time_value)
        except ValueError as exc:
            raise ValueError(
                "AI returned an invalid meeting time."
            ) from exc

        if meeting_time.strftime("%H:%M") != time_value:
            raise ValueError(
                "Meeting time must use HH:MM format."
            )

    # If the date is missing but a weekday is known, calculate
    # the next upcoming occurrence of that weekday.
    if meeting_date is None and weekday is not None:
        days_ahead = (weekday - today.weekday()) % 7

        # A weekday-only proposal means the next occurrence.
        # If today is that weekday, choose the following week.
        if days_ahead == 0:
            days_ahead = 7

        meeting_date = today + timedelta(days=days_ahead)

    # Check whether the AI's date matches the stated weekday.
    if (
        meeting_date is not None
        and weekday is not None
        and meeting_date.weekday() != weekday
    ):
        if explicit_date:
            raise ValueError(
                "The meeting date does not match the stated weekday."
            )

        # The conversation specified a weekday but not an explicit
        # calendar date, so correct the AI's incorrect date.
        days_ahead = (weekday - today.weekday()) % 7

        if days_ahead == 0:
            days_ahead = 7

        meeting_date = today + timedelta(days=days_ahead)

    # We cannot determine whether the meeting time has passed
    # unless both the date and time are available.
    if meeting_date is not None and meeting_time is not None:
        meeting_datetime = datetime.combine(
            meeting_date,
            meeting_time,
            tzinfo=PAKISTAN_TZ,
        )

        if meeting_datetime < now:
            if explicit_date or weekday is None:
                raise ValueError(
                    "Meeting date and time cannot be in the past."
                )

            # The date was inferred from a weekday. Move it to
            # the next occurrence instead of using a past date.
            days_ahead = (weekday - today.weekday()) % 7

            if days_ahead == 0:
                days_ahead = 7

            meeting_date = today + timedelta(days=days_ahead)

    validated_date = (
        meeting_date.isoformat()
        if meeting_date is not None
        else None
    )

    validated_time = (
        meeting_time.strftime("%H:%M")
        if meeting_time is not None
        else None
    )

    return validated_date, validated_time


# --------------------------------------------------
# Meeting analysis instructions
# --------------------------------------------------

MEETING_ANALYSIS_RULES = """
Analyze the conversation and identify the proposed meeting,
its details, and each group member's response.

1. SPEAKERS AND PROPOSER

- Identify the person who originally proposed the meeting.
- Every conversation message includes a user ID and display name.
- Return the proposer's exact ID in proposed_by_user_id.
- The ID must match a user ID appearing in the conversation.
- Never identify the proposer by name alone.
- Never invent or guess a user ID.
- If the proposer cannot be identified confidently, return null.
- The proposer initially counts as agreed unless they explicitly
  decline or withdraw their agreement.

2. INTERPRETING RESPONSES

- Interpret replies in the context of the full conversation.
- "Yes", "yeah", "I'm in", "sure", and "sounds good"
  count as agreement when clearly responding to the proposal.
- Clear refusals such as "no", "I cannot attend", and
  "I won't be able to make it" count as declined.
- A suggestion or alternative alone is not an agreement.
- Silence does not count as agreement for non-proposers.
- Use "unknown" when a person's response is unclear.
- Do not classify a person as declined without evidence
  of an actual refusal.
- If someone agrees and later explicitly withdraws,
  their final response must be declined.
- Use the person's latest clear decision about attendance.
- This withdrawal rule applies to the proposer too.
- One person's refusal must not affect another person's status.

3. PARTICIPANT RESPONSES

- Include every identifiable person who speaks in the conversation.
- Identify each person by their exact user_id.
- Include the person's name and final response.
- Each response must be exactly "agreed", "declined", or "unknown".
- Include each user_id only once.
- The proposer initially counts as agreed unless they explicitly
  withdraw or clearly decline attendance.
- Never invent user IDs, names, or responses.
- Different user IDs represent different people even if their
  display names are identical.

4. PARTICIPANTS AND MEETING AGREEMENT

- participants must contain only people whose final response
  is agreed.
- Each participant must include user_id and name.
- Include the proposer when their final response is agreed.
- Exclude anyone whose response is declined or unknown.
- Count distinct participants by user_id, not by name.
- If at least two distinct user IDs agreed, meeting_agreed is true.
- Otherwise, meeting_agreed is false.
- One person's refusal must not affect another person's status.

5. MEETING TITLE AND DETAILS

- Extract only details supported by the conversation.
- Generate a short, meaningful title when the activity is clear.
- For example, a proposal to go out on Sunday may use
  the title "Sunday Outing".
- Do not require a formal title in the conversation.
- Return null for the title only if the activity cannot
  reasonably be determined.
- Never invent dates, times, durations, or identities.
- Duration is optional. If not specified, return null.
- Do not request clarification solely because duration is unknown.
- Return dates in YYYY-MM-DD format.
- Return times in 24-hour HH:MM format.
- Use null for unknown optional details.

6. WEEKDAY AND CALENDAR DATE

- Use the supplied current date in Pakistan when interpreting
  relative dates and weekdays.
- Calculate future weekdays relative to today's date.
- The returned date must match the stated weekday.
- Never silently change the stated weekday.
- If a weekday is specified, populate the weekday field.
- The date and weekday must agree.
- If an essential date or time cannot be determined,
  set needs_clarification to true and explain what is missing.
- Otherwise, set needs_clarification to false.
- Do not request clarification for optional details.

- When the conversation says "Sunday" without specifying a date,
  select the next upcoming Sunday relative to today's date.
- If today is Sunday, interpret "Sunday" as today only if the
  conversation clearly refers to today; otherwise choose next Sunday.
- Calculate the calendar date carefully before returning it.
- Never return a Saturday date when the requested weekday is Sunday.

7. FINAL CONSISTENCY CHECK

- Verify each person's final response against the conversation.
- Ensure the proposer is included in participant_responses.
- Ensure participants contains only people marked agreed.
- Ensure meeting_agreed matches the number of distinct
  agreeing participants.
- Ensure the date matches the weekday.
- Return only information supported by the conversation.
"""


# --------------------------------------------------
# Extract IDs and names present in the conversation
# --------------------------------------------------

def get_conversation_members(conversation: str) -> dict[int, str]:
    """
    Expected message format:

    [User ID: 12] Ahmed: Let's meet on Sunday.
    """

    members: dict[int, str] = {}

    pattern = re.compile(
        r"^\[User ID:\s*(\d+)\]\s*(.+?):\s*",
        re.IGNORECASE,
    )

    for line in conversation.splitlines():
        match = pattern.match(line.strip())

        if not match:
            continue

        user_id = int(match.group(1))
        name = match.group(2).strip()

        if user_id > 0 and name:
            # Preserve the first name encountered for this ID.
            members.setdefault(user_id, name)

    return members


# --------------------------------------------------
# Analyze a conversation
# --------------------------------------------------

async def analyze_meeting(conversation: str) -> dict:
    if not conversation or not conversation.strip():
        raise ValueError("Conversation cannot be empty")

    conversation_members = get_conversation_members(conversation)

    if not conversation_members:
        raise ValueError(
            "No valid user IDs found in the conversation. "
            "Expected format: [User ID: 1] Ahmed: message"
        )

    today = datetime.now(PAKISTAN_TZ).date().isoformat()

    system_prompt = f"""
You are a meeting assistant for a messaging application.

Today's date in Pakistan is {today}.

Analyze the conversation and identify whether a meeting
has been agreed upon.

Follow these rules carefully:

{MEETING_ANALYSIS_RULES}
"""

    response = await client.chat.completions.create(
        model="openai/gpt-oss-20b",
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": (
                    "Analyze this conversation:\n\n"
                    f"{conversation}"
                ),
            },
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "meeting_details",
                "strict": True,
                "schema": make_groq_compatible_schema(
                    MeetingDetails.model_json_schema()
                ),
            },
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("Groq returned an empty response")

    meeting = MeetingDetails.model_validate_json(content)
    result = meeting.model_dump()

    # --------------------------------------------------
    # Validate the date and time returned by the AI
    # --------------------------------------------------

    result["date"], result["time"] = validate_meeting_datetime(
        date_value=result["date"],
        time_value=result["time"],
        weekday_value=result["weekday"],
        conversation=conversation,
    )

    # --------------------------------------------------
    # Normalize responses using unique user IDs
    # --------------------------------------------------

    responses_by_id: dict[int, dict] = {}

    for participant in result["participant_responses"]:
        user_id = participant["user_id"]
        status = participant["response"].strip().casefold()

        # Do not trust IDs that do not appear in this conversation.
        if user_id not in conversation_members:
            continue

        # Use the backend-provided name, not an AI-generated name.
        actual_name = conversation_members[user_id]

        if status not in VALID_RESPONSES:
            status = "unknown"

        # Each user ID represents one person.
        responses_by_id[user_id] = {
            "user_id": user_id,
            "name": actual_name,
            "response": status,
        }

    # --------------------------------------------------
    # Validate and normalize the proposer
    # --------------------------------------------------

    proposer_id = result["proposed_by_user_id"]

    if proposer_id not in conversation_members:
        proposer_id = None

    result["proposed_by_user_id"] = proposer_id

    if proposer_id is not None:
        proposer_response = responses_by_id.get(proposer_id)

        if proposer_response is None:
            # Recover a missing proposer using the ID and name
            # associated with them in the actual conversation.
            responses_by_id[proposer_id] = {
                "user_id": proposer_id,
                "name": conversation_members[proposer_id],
                "response": "agreed",
            }

        elif proposer_response["response"] == "unknown":
            # The proposer initially agrees unless they explicitly
            # decline or withdraw. Preserve explicit declines.
            proposer_response["response"] = "agreed"

    # --------------------------------------------------
    # Save normalized participant responses
    # --------------------------------------------------

    result["participant_responses"] = list(
        responses_by_id.values()
    )

    # --------------------------------------------------
    # Derive agreed participants from final responses
    # --------------------------------------------------

    agreed_participants = [
        {
            "user_id": participant["user_id"],
            "name": participant["name"],
        }
        for participant in result["participant_responses"]
        if participant["response"] == "agreed"
    ]

    result["participants"] = agreed_participants

    # --------------------------------------------------
    # Determine meeting agreement using distinct IDs
    # --------------------------------------------------

    agreed_user_ids = {
        participant["user_id"]
        for participant in agreed_participants
    }

    result["meeting_agreed"] = len(agreed_user_ids) >= 2

    if result["meeting_agreed"]:
        result["needs_clarification"] = False
        result["clarification_question"] = None

    elif not result["needs_clarification"]:
        # Do not invent a clarification question when the AI
        # has already determined that clarification is unnecessary.
        result["clarification_question"] = None

    return result
