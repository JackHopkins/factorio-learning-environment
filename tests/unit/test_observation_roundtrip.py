"""Observation.to_dict() -> Observation.from_dict() must round-trip without a live server.

to_dict() writes the string "None" for an empty research ``progress`` and for a missing
``current_research``. from_dict() used to iterate that string and crash with
``TypeError: string indices must be integers``, which happens on the observation returned by
``FactorioGymEnv.reset()`` in a fresh game with nothing researched.
"""

from fle.agents.models import TaskResponse
from fle.commons.models.achievements import ProductionFlows
from fle.commons.models.research_state import ResearchState
from fle.env.gym_env.observation import GameInfo, Observation


def _observation(research: ResearchState) -> Observation:
    return Observation(
        raw_text="",
        entities=[],
        inventory={"coal": 5},
        research=research,
        game_info=GameInfo(tick=0, time=0.0, speed=1.0),
        score=0.0,
        automated_score=0.0,
        flows=ProductionFlows(
            input={},
            output={},
            crafted=[],
            harvested={},
            price_list={},
            static_items={},
        ),
        task_verification=TaskResponse(success=False, meta={}),
        messages=[],
        serialized_functions=[],
        task_info=None,
        map_image="",
        character_positions=[],
    )


def test_round_trip_with_nothing_researched():
    """A fresh game: no current research and no progress entries."""
    research = ResearchState(
        technologies={},
        current_research=None,
        research_progress=0.0,
        research_queue=[],
        progress={},
    )
    obs_dict = _observation(research).to_dict()
    assert obs_dict["research"]["progress"] == "None"  # the sentinel to_dict() emits

    restored = Observation.from_dict(obs_dict)

    assert restored.research.progress == {}
    assert restored.research.current_research is None
    assert restored.inventory["coal"] == 5


def test_round_trip_with_research_in_progress():
    """The populated case keeps working."""
    research = ResearchState(
        technologies={},
        current_research="automation",
        research_progress=0.5,
        research_queue=["automation"],
        progress={"automation": 0.5},
    )
    restored = Observation.from_dict(_observation(research).to_dict())

    assert restored.research.progress == {"automation": 0.5}
    assert restored.research.current_research == "automation"
