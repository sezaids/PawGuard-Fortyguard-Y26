from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.services.safety_assistant import base_context, live_multi_dog_answer, profile_guidance_answer


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


def test_profile_fallback_compares_every_dog_for_pack_question():
    bella = SimpleNamespace(id=uuid4(), name="Bella", body_size="large", coat_color="black", coat_length="double", brachycephalic=True, activity_level="high", fitness_level="low", weight_kg=36, date_of_birth=date(2017, 1, 1))
    luna = SimpleNamespace(id=uuid4(), name="Luna", body_size="medium", coat_color="cream", coat_length="short", brachycephalic=False, activity_level="low", fitness_level="high", weight_kg=16, date_of_birth=date(2022, 1, 1))

    answer = profile_guidance_answer("Can you tell which dog I can walk now and why?", [bella, luna])

    assert answer.startswith("Profile-based guidance only: Luna has the lowest relative heat sensitivity")
    assert "Bella (" in answer
    assert "Luna (" in answer
    assert answer.count("cannot confirm whether walking is currently safe") == 1


def test_live_multi_dog_answer_preserves_walk_match_ranking_and_avoidance():
    result = {
        "best_match": {"dog_name": "Luna", "status": "Low", "estimated_risk": 12, "recommended_duration_minutes": 30, "main_factors": []},
        "ranked_matches": [
            {"dog_name": "Luna", "status": "Low", "estimated_risk": 12, "recommended_duration_minutes": 30, "suitable": True, "main_factors": []},
            {"dog_name": "Bella", "status": "High", "estimated_risk": 67, "recommended_duration_minutes": 10, "suitable": False, "main_factors": [{"factor": "Short-nosed (brachycephalic)"}]},
        ],
        "avoid": [{"dog_name": "Bella", "status": "High", "estimated_risk": 67, "main_factors": [{"factor": "Short-nosed (brachycephalic)"}]}],
    }

    answer = live_multi_dog_answer(result)

    assert answer.startswith("Walk Luna now")
    assert "Bella" in answer
    assert "High 67/100" in answer


def test_live_multi_dog_answer_handles_an_empty_pack():
    assert "Add dog profiles" in live_multi_dog_answer(None)
