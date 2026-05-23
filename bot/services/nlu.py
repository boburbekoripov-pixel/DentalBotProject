from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Literal

from openai import AsyncOpenAI
from openai.types.chat import ChatCompletionMessageParam
from pydantic import BaseModel, Field

from bot.db.schemas import ConversationMessage, EventDraft

logger = logging.getLogger(__name__)


Intent = Literal[
    "create_event",
    "update_event",
    "delete_event",
    "query_schedule",
    "small_talk",
    "clarify",
]


class NLUResult(BaseModel):
    """Structured output returned by GPT for every user message."""

    intent: Intent
    # Filled when intent involves an event lifecycle action.
    draft: EventDraft | None = None
    # Set when more info is needed to complete the draft.
    needs_clarification: bool = False
    clarification_question: str | None = None
    # Free-form assistant reply (for small_talk or query_schedule).
    reply: str | None = None
    # When intent=delete/update, identifier hint (LLM-extracted title fragment).
    target_event_hint: str | None = Field(
        default=None,
        description="Snippet to match an existing event for delete/update intents",
    )


SYSTEM_PROMPT = """You are a strict NLU/dialogue engine for a personal planner bot.
The user writes in Russian, Uzbek or English (often mixed). Reply texts you produce
must be in the user's language (default Russian).

CONTEXT
- Current local datetime: {now_iso}
- Timezone: {tz}
- Recent events (next 7 days): {recent_events}
- Pending draft (if any): {pending_draft}

You return ONE JSON object matching this schema (no prose outside JSON):
{schema}

INTENT RULES
- "create_event" — user wants a new meeting / task / reminder
- "update_event" — user wants to change an existing one (set target_event_hint)
- "delete_event" — user wants to cancel one (set target_event_hint)
- "query_schedule" — user asks "what's tomorrow?", "когда у меня X?". Write the answer in `reply`.
- "small_talk" — greeting / chat / off-topic. Write the answer in `reply`.
- "clarify" — when the user message answers a previous clarification_question and just
  contributes missing info to the pending draft.

DATE/TIME PARSING
- "сегодня"/"today" → today's date
- "завтра"/"tomorrow" → tomorrow
- "послезавтра" → +2 days
- "через X часов/минут" → now + X
- "в понедельник" → next Monday (if today is Monday and time has passed → next week)
- "вечером" without time → ask clarification "Во сколько вечером?"
- "утром" → ask "Во сколько утром?"
- ALWAYS produce start_at in ISO 8601 with the user's timezone offset.
- If date is given but no time → ask for time.
- If time is given but no date → assume today if time still in future, else tomorrow.

RECURRENCE
- "каждый день" → freq=daily
- "каждый понедельник" → freq=weekly, byweekday=["MO"]
- "по будням" → freq=weekly, byweekday=["MO","TU","WE","TH","FR"]
- "каждое утро" → freq=daily + ask for time if not given

REMINDERS
- "напомни за 20 минут" → reminder_offsets_minutes=[20]
- "напомни за час и за 10 минут" → [60, 10]
- Default if nothing said: [15]

CLARIFICATION
- If something critical is missing (title, date, time), set needs_clarification=true
  and ask ONE concise question in clarification_question, in the user's language.
- Don't ask for non-critical fields (location, notes) — leave them null.
- For "напомни через X" with no title → ask "О чём напомнить?"

EXAMPLES
"завтра в 9 встреча с Джахонгиром" → intent=create_event,
  draft={title:"Встреча с Джахонгиром", start_at:"<tomorrow>T09:00", participants:["Джахонгир"]}
"напомни за 20 минут" (with pending draft) → intent=clarify,
  draft={reminder_offsets_minutes:[20]}
"что у меня завтра?" → intent=query_schedule, reply="<list events>"
"привет" → intent=small_talk, reply="Привет! Чем помочь?"
"""


class NLUService:
    def __init__(self, client: AsyncOpenAI, model: str) -> None:
        self._client = client
        self._model = model

    async def extract(
        self,
        text: str,
        *,
        now: datetime,
        timezone: str,
        recent_events: str,
        pending_draft: EventDraft | None,
        history: list[ConversationMessage],
    ) -> NLUResult:
        system_content = SYSTEM_PROMPT.format(
            now_iso=now.isoformat(),
            tz=timezone,
            recent_events=recent_events or "(none)",
            pending_draft=(
                json.dumps(pending_draft.model_dump(mode="json"), ensure_ascii=False)
                if pending_draft
                else "(none)"
            ),
            schema=json.dumps(NLUResult.model_json_schema(), ensure_ascii=False),
        )
        messages: list[ChatCompletionMessageParam] = [
            {"role": "system", "content": system_content},
        ]
        for m in history[-6:]:
            if m.role == "user":
                messages.append({"role": "user", "content": m.content})
            elif m.role == "assistant":
                messages.append({"role": "assistant", "content": m.content})
        messages.append({"role": "user", "content": text})

        # Use json_object mode — gpt-4o-mini supports it and it's much cheaper
        # than fully validated structured outputs while still reliable.
        response = await self._client.chat.completions.create(
            model=self._model,
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.1,
        )
        raw = response.choices[0].message.content or "{}"
        try:
            data = json.loads(raw)
            return NLUResult.model_validate(data)
        except Exception:
            logger.exception("Failed to parse NLU output: %s", raw)
            return NLUResult(
                intent="small_talk",
                reply="Не понял запрос, попробуй переформулировать.",
            )
