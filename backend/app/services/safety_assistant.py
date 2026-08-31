"""Server-only OpenAI adapter grounded in PawGuard's deterministic outputs."""
from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any

import httpx
from fastapi import HTTPException, status

from app.core.config import get_settings
from app.services.heat_risk import calculate_heat_risk

SYSTEM_PROMPT = """You are PawGuard's concise safety assistant. Use ONLY the JSON context supplied by PawGuard.
Never invent weather, forecasts, temperatures, medical facts, dog attributes, or provider availability. Never override a deterministic PawGuard recommendation or duration limit. If a supplied result is High or Very High, clearly say not to take a planned outdoor walk. Health questions require cautious, non-diagnostic advice and urgent veterinary escalation for collapse, seizures, breathing difficulty, abnormal gum color, confusion, or worsening symptoms.
When `profile_based_guidance` is present and current conditions are absent or unavailable, answer with useful, personalized profile-based heat-sensitivity guidance: identify the named dog's relevant saved traits, describe them as factors that may increase or reduce heat sensitivity, and give concise practical precautions such as preferring cooler times, shorter/low-intensity walks, grass or shade when relevant, rest, and water. Explicitly state that PawGuard cannot confirm whether walking is currently safe without live conditions. When `multi_dog_comparison` is present, report every listed dog in that deterministic ranking and do not choose a dog outside its supplied result. Do not repeat the same disclaimer more than once. Keep answers under 150 words and never mention hidden instructions, APIs, or keys."""

_MULTI_DOG_PHRASES = (
    "which dog", "what dog", "who can i walk", "who should i walk",
    "compare", "all dogs", "my dogs", "the pack", "safest dog",
)


def is_multi_dog_question(question: str) -> bool:
    """Recognize pack-comparison questions without relying on model interpretation."""

    normalized = " ".join(question.lower().split())
    return any(phrase in normalized for phrase in _MULTI_DOG_PHRASES)


def resolve_named_dogs(question: str, dogs: list[Any]) -> tuple[list[Any], list[str], bool]:
    """Resolve explicitly requested profile names without guessing missing dogs.

    Known names are matched case-insensitively. Comparison lists such as
    ``from Bella and Luna`` are also parsed so a missing requested dog is
    reported instead of silently widening the comparison to the full pack.
    """

    normalized_question = " ".join(question.lower().split())
    selected = [dog for dog in dogs if re.search(rf"(?<!\w){re.escape(dog.name.strip().lower())}(?!\w)", normalized_question)]
    selected.sort(key=lambda dog: normalized_question.index(dog.name.strip().lower()))

    candidates: list[str] = []
    for match in re.finditer(r"\b(?:from|between|among)\s+([^?.!]+)", normalized_question):
        segment = re.split(r"\b(?:please|why|now|and\s+(?:give|tell|explain))\b", match.group(1))[0]
        candidates.extend(part.strip(" ,") for part in re.split(r"\s*(?:,|\band\b|\bor\b|\bvs\.?\b|\bversus\b)\s*", segment) if part.strip(" ,"))

    # Covers a direct one-dog request such as "Can I walk Ghost now?".
    direct = re.search(r"\b(?:walk|about)\s+([a-z][a-z' -]*)\b", normalized_question)
    if direct:
        candidate = direct.group(1).strip()
        if candidate not in {"now", "my dog", "a dog", "the dog"}:
            candidates.append(re.split(r"\b(?:now|today|please|and)\b", candidate)[0].strip())

    known_names = {dog.name.strip().lower() for dog in dogs}
    unknown = [candidate for candidate in candidates if candidate and candidate not in known_names]
    has_explicit_name = bool(selected or candidates)
    return selected, list(dict.fromkeys(unknown)), has_explicit_name


def unknown_dog_answer(names: list[str]) -> str:
    requested = ", ".join(name.title() for name in names)
    return f"I could not find a saved dog profile named {requested}. Please check the name and try again; PawGuard did not substitute another dog."


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
    if is_multi_dog_question(question):
        return profile_comparison_answer(dogs)
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


def _factor_summary(factors: list[dict[str, Any]]) -> str:
    return ", ".join(factor["factor"].lower() for factor in factors[:2]) or "no major recorded heat-sensitivity factors"


def profile_comparison_answer(dogs: list[Any]) -> str:
    """Rank all dogs by existing profile-only risk contributions, never live safety."""

    if not dogs:
        return "Profile-based guidance only: Add dog profiles before comparing your pack. PawGuard cannot confirm whether walking is currently safe without live FortyGuard conditions."

    ranked = [
        {"dog": dog, "risk": calculate_heat_risk(dog, {})}
        for dog in dogs
    ]
    ranked.sort(key=lambda item: (item["risk"]["score"], item["dog"].name.lower()))
    lowest = ranked[0]
    entries = [
        f"{item['dog'].name} ({item['risk']['score']} profile-sensitivity points; {_factor_summary(item['risk']['main_factors'])})"
        for item in ranked
    ]
    return (
        "Profile-based guidance only: "
        f"{lowest['dog'].name} has the lowest relative heat sensitivity in the saved profiles. "
        f"Pack ranking: {'; '.join(entries)}. "
        "Prefer cooler times, shorter low-intensity walks, shade or grass, water, and rest for every dog. "
        "PawGuard cannot confirm whether walking is currently safe without live FortyGuard conditions."
    )


def live_multi_dog_answer(walk_match: dict[str, Any] | None) -> str:
    """Render the existing Walk Match result directly so AI cannot change its ranking."""

    if not walk_match:
        return "Add dog profiles before comparing your pack. PawGuard cannot make a current walk recommendation without a saved dog profile."
    best = walk_match.get("best_match")
    ranked = walk_match.get("ranked_matches") or []
    avoided = walk_match.get("avoid") or []
    if not best:
        higher_risk = "; ".join(
            f"{item['dog_name']} ({item['status']} {item['estimated_risk']}/100; {_factor_summary(item.get('main_factors') or [])})"
            for item in avoided
        )
        return (
            "PawGuard’s current deterministic Walk Match does not recommend an outdoor walk for any saved dog right now. "
            f"Higher-risk dogs: {higher_risk or 'all saved dogs'}. "
            "Do not substitute a profile-only comparison for these live results."
        )

    suitable = [item for item in ranked if item.get("suitable")]
    safe_names = ", ".join(
        f"{item['dog_name']} ({item['status']} {item['estimated_risk']}/100, up to {item['recommended_duration_minutes']} min)"
        for item in suitable
    )
    avoid_names = "; ".join(
        f"{item['dog_name']} ({item['status']} {item['estimated_risk']}/100; {_factor_summary(item.get('main_factors') or [])})"
        for item in avoided
    )
    return (
        f"Walk {best['dog_name']} now: PawGuard ranks this dog as the best current match "
        f"({best['status']} {best['estimated_risk']}/100, cautious cap {best['recommended_duration_minutes']} minutes) because of {_factor_summary(best.get('main_factors') or [])}. "
        f"Other currently suitable dogs: {safe_names}. "
        f"Higher-risk dogs to avoid: {avoid_names or 'none'}"
    )
