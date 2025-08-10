import json
from typing import Dict, Any

from strands import Agent
from strands.models.anthropic import (
    AnthropicModel,
)  # pip install 'strands-agents[anthropic]'

from app.schemas.plan import PlanPayload
from app.core.config import settings

SYSTEM = (
    "You are a precise executive assistant. Respond with STRICT JSON ONLY matching this schema: "
    '{"eisenhower":{"urgent_important":[],"urgent_not_important":[],"not_urgent_important":[],"not_urgent_not_important":[]},'
    '"three_needles":{"money":"","health":"","relationships":""},'
    '"schedule":[{"start":"HH:mm","end":"HH:mm","item":""}],'
    '"affirmations":{"am":"","pm":""},'
    '"stress_guide":[{"trigger":"","action":""}],'
    '"nudges":[{"at":"HH:mm","msg":""}]} '
    "Rules: honor user timezone and events; prefer 06:30–21:00 unless events force otherwise. "
    "Do not include any text outside the JSON."
)


async def call_claude(context: Dict[str, Any]) -> PlanPayload:
    """Use the same Strands+Anthropic stack as chat. Fall back locally on any error."""
    if not settings.anthropic_key:
        return local_plan(context)

    try:
        model = AnthropicModel(
            client_args={"api_key": settings.anthropic_key},
            model_id="claude-3-5-sonnet-20240620",
            max_tokens=1400,
            params={"temperature": 0.4},
        )
        agent = Agent(model=model, system_prompt=SYSTEM)
        # Pass just the context JSON; the system prompt defines the format.
        result = await agent.invoke_async(json.dumps(context, default=str))
        text = str(result).strip()

        # Parse directly into your Pydantic schema. If it fails, use local fallback.
        try:
            return PlanPayload.model_validate_json(text)
        except Exception:
            # Some models wrap JSON in prose; try to extract the first {...}
            import re

            m = re.search(r"\{[\s\S]*\}", text)
            if not m:
                return local_plan(context)
            return PlanPayload.model_validate_json(m.group(0))
    except Exception as e:
        # Any SDK/network/model error -> safe fallback
        print("Planner (Strands) error:", repr(e))
        return local_plan(context)


def local_plan(context: dict) -> PlanPayload:
    """Deterministic plan so the UI never breaks."""
    tasks = [t.get("title", "Task") for t in context.get("tasks", [])]
    top = tasks[:4]
    rest = tasks[4:8]
    schedule = [
        {"start": "06:45", "end": "07:00", "item": "Hydrate + plan review"},
        {"start": "07:00", "end": "07:30", "item": "Meditation"},
        {"start": "07:30", "end": "08:10", "item": "Skips/Yoga"},
        {"start": "08:10", "end": "09:00", "item": "Deep Work Block #1"},
    ]
    nudges = [
        {"at": "10:55", "msg": "Stand & water"},
        {"at": "18:00", "msg": "Strength 30m"},
    ]
    return PlanPayload(
        eisenhower={
            "urgent_important": top[:2],
            "urgent_not_important": rest[:2],
            "not_urgent_important": top[2:4],
            "not_urgent_not_important": rest[2:4],
        },
        three_needles={
            "money": "Close one revenue/opportunity task",
            "health": "500 skips + 3-mile walk",
            "relationships": "Message a key friend",
        },
        schedule=schedule,
        affirmations={
            "am": "I move the big rocks first.",
            "pm": "I celebrate progress, big or small.",
        },
        stress_guide=[
            {
                "trigger": "calendar overload",
                "action": "Declutter + 3-min box breathing",
            }
        ],
        nudges=nudges,
    )
