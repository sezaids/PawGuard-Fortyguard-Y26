from datetime import date
from types import SimpleNamespace
from uuid import uuid4

from app.services.safety_assistant import base_context, live_multi_dog_answer, profile_guidance_answer, resolve_named_dogs, unknown_dog_answer


def dog(name: str, **overrides):
    defaults = dict(id=uuid4(), name=name, body_size="medium", coat_color="cream", coat_length="short", brachycephalic=False, activity_level="low", fitness_level="high", weight_kg=16, date_of_birth=date(2022, 1, 1))
    return SimpleNamespace(**(defaults | overrides))


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


def test_named_pair_limits_comparison_to_bella_and_luna_case_insensitively():
    dogs = [dog("Max"), dog("Bella"), dog("Luna"), dog("Bruno")]

    selected, unknown, explicit = resolve_named_dogs("Which dog should I walk now from bella and LUNA?", dogs)

    assert explicit is True
    assert unknown == []
    assert [item.name for item in selected] == ["Bella", "Luna"]


def test_one_named_dog_selects_only_that_dog():
    dogs = [dog("Max"), dog("Bella"), dog("Luna")]

    selected, unknown, explicit = resolve_named_dogs("Can I walk Luna now?", dogs)

    assert explicit is True
    assert unknown == []
    assert [item.name for item in selected] == ["Luna"]


def test_no_named_dog_leaves_the_full_pack_available():
    dogs = [dog("Max"), dog("Bella"), dog("Luna")]

    selected, unknown, explicit = resolve_named_dogs("Which of my dogs should I walk now?", dogs)

    assert selected == []
    assert unknown == []
    assert explicit is False


def test_unknown_requested_dog_is_reported_without_substitution():
    selected, unknown, explicit = resolve_named_dogs("Can I walk Ghost now?", [dog("Bella"), dog("Luna")])

    assert selected == []
    assert explicit is True
    assert unknown == ["ghost"]
    assert "Ghost" in unknown_dog_answer(unknown)
