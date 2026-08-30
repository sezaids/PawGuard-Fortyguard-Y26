from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.services.safety_assistant import base_context, profile_guidance_answer


def test_assistant_context_excludes_account_email_and_notes():
    dog = SimpleNamespace(id=uuid4(), name="Max", body_size="medium", coat_color="black", coat_length="short", brachycephalic=False, activity_level="moderate", fitness_level="average", weight_kg=18, date_of_birth=date(2022, 1, 1), notes="private note")
    context = base_context([dog])
    assert "email" not in str(context).lower()
    assert "private note" not in str(context)
    assert context["dogs"][0]["name"] == "Max"
    assert "dark black coat color" in context["profile_based_guidance"][0]["factors"]


def test_profile_fallback_is_max_specific_and_has_one_live_data_caveat():
    max_dog = SimpleNamespace(id=uuid4(), name="Max", body_size="large", coat_color="black", coat_length="short", brachycephalic=False, activity_level="high", fitness_level="average", weight_kg=28, date_of_birth=date(2022, 1, 1))
    answer = profile_guidance_answer("Can I walk Max now?", [max_dog])
    assert answer.startswith("Profile-based guidance only: Max's saved profile")
    assert "large body size" in answer
    assert "high activity level" in answer
    assert answer.count("cannot confirm whether walking is currently safe") == 1
