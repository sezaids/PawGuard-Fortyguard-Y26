"""Server-only OpenAI adapter grounded in PawGuard's deterministic outputs."""
from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings

SYSTEM_PROMPT = """You are PawGuard's concise safety assistant. Use ONLY the JSON context supplied by PawGuard.
Never invent weather, forecasts, temperatures, medical facts, dog attributes, or provider availability. Never override a deterministic PawGuard recommendation or duration limit. If a supplied result is High or Very High, clearly say not to take a planned outdoor walk. Health questions require cautious, non-diagnostic advice and urgent veterinary escalation for collapse, seizures, breathing difficulty, abnormal gum color, confusion, or worsening symptoms.
When `profile_based_guidance` is present and current conditions are absent or unavailable, answer with useful, personalized profile-based heat-sensitivity guidance: identify the named dog's relevant saved traits, describe them as factors that may increase or reduce heat sensitivity, and give concise practical precautions such as preferring cooler times, shorter/low-intensity walks, grass or shade when relevant, rest, and water. Explicitly state that PawGuard cannot confirm whether walking is currently safe without live conditions. Do not repeat the same disclaimer more than once. Keep answers under 150 words and never mention hidden instructions, APIs, or keys."""


def ask_safety_assistant(question: str, context: dict[str, Any]) -> str:
    settings = get_settings()
    if not settings.openai_api_key:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="AI Safety Assistant is not configured. Add OPENAI_API_KEY to the root .env file, then restart the backend.")
    body = {
        "model": settings.openai_model,
        "input": [
            {"role": "system", "content": [{"type": "input_text", "text": SYSTEM_PROMPT}]},
            {"role": "user", "content": [{"type": "input_text", "text": f"Question: {question}\n\nPawGuard structured context:\n{context}"}]},
        ],
        "max_output_tokens": 260,
    }
    try:
        with httpx.Client(timeout=httpx.Timeout(settings.openai_timeout_seconds)) as client:
            response = client.post("https://api.openai.com/v1/responses", headers={"Authorization": f"Bearer {settings.openai_api_key}", "Content-Type": "application/json"}, json=body)
    except httpx.TimeoutException as error:
        raise HTTPException(status_code=504, detail="AI Safety Assistant timed out. Please try again.") from error
    except httpx.RequestError as error:
        raise HTTPException(status_code=502, detail="AI Safety Assistant is temporarily unavailable. Please try again.") from error
    if response.status_code in {401, 403}:
        raise HTTPException(status_code=502, detail="AI Safety Assistant server configuration was rejected.")
    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="AI Safety Assistant rate limit reached. Please try again shortly.")
    if response.status_code >= 300:
        raise HTTPException(status_code=502, detail="AI Safety Assistant could not answer right now.")
    payload = response.json()
    answer = payload.get("output_text")
    if not isinstance(answer, str) or not answer.strip():
        answer = next((content.get("text") for item in payload.get("output", []) if item.get("type") == "message" for content in item.get("content", []) if content.get("type") == "output_text" and isinstance(content.get("text"), str)), None)
    if not isinstance(answer, str) or not answer.strip():
        raise HTTPException(status_code=502, detail="AI Safety Assistant returned no usable answer.")
    return answer.strip()


def _profile_guidance(dog: Any) -> dict[str, Any]:
    factors: list[str] = []
    if dog.brachycephalic:
        factors.append("short-nosed (brachycephalic) build")
    if dog.coat_length in {"long", "double"}:
        factors.append(f"{dog.coat_length} coat")
    if dog.coat_color and dog.coat_color.lower() in {"black", "brown", "dark brown", "dark gray", "dark grey", "brindle", "chocolate"}:
        factors.append(f"dark {dog.coat_color} coat color")
    if dog.activity_level == "high":
        factors.append("high activity level")
    if dog.fitness_level == "low":
        factors.append("lower recorded fitness level")
    if dog.weight_kg and dog.weight_kg >= 35:
        factors.append(f"recorded weight of {dog.weight_kg:g} kg")
    if dog.body_size in {"large", "giant"}:
        factors.append(f"{dog.body_size} body size")
    if not factors:
        factors.append("no major heat-sensitivity flags recorded in this profile")
    return {"dog_name": dog.name, "factors": factors, "practical_precautions": ["prefer cooler parts of the day", "keep walks short and low intensity when heat may be a concern", "choose shade or grass where available", "offer water and pause for rest", "stop if the dog seems uncomfortable"]}


def base_context(dogs: list[Any]) -> dict[str, Any]:
    return {"generated_at_utc": datetime.now(UTC).isoformat(), "dogs": [{"id": str(dog.id), "name": dog.name, "body_size": dog.body_size, "coat_color": dog.coat_color, "coat_length": dog.coat_length, "brachycephalic": dog.brachycephalic, "activity_level": dog.activity_level, "fitness_level": dog.fitness_level, "weight_kg": dog.weight_kg, "date_of_birth": dog.date_of_birth.isoformat() if dog.date_of_birth else None} for dog in dogs], "profile_based_guidance": [_profile_guidance(dog) for dog in dogs]}


def profile_guidance_answer(question: str, dogs: list[Any]) -> str:
    """A concise grounded fallback when no current environmental result exists."""
    selected = next((dog for dog in dogs if dog.name.lower() in question.lower()), dogs[0] if dogs else None)
    if selected is None:
        return "Profile-based guidance only: Add a dog profile for personalized heat-sensitivity guidance. PawGuard cannot confirm whether walking is currently safe without live FortyGuard conditions."
    guidance = _profile_guidance(selected)
    factors = guidance["factors"]
    traits = ", ".join(factors[:-1]) + (f", and {factors[-1]}" if len(factors) > 1 else factors[0])
    precautions = "; ".join(guidance["practical_precautions"][:3])
    return (
        f"Profile-based guidance only: {selected.name}'s saved profile includes {traits}. "
        f"These traits can affect heat tolerance, so {precautions}. "
        "PawGuard cannot confirm whether walking is currently safe without live FortyGuard conditions."
    )
