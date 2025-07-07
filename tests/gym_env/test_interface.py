import pytest
from gym import spaces

from fle.env.gym_env.environment import FactorioGymEnv
from fle.env.gym_env.action import Action


@pytest.fixture
def env(instance):
    env = FactorioGymEnv(instance)
    yield env
    env.close()


def test_gym_env_interface(env):
    # Check action_space and observation_space are gym.spaces.Dict
    assert isinstance(env.action_space, spaces.Dict)
    assert isinstance(env.observation_space, spaces.Dict)
    # Check reset returns (obs, info)
    obs, info = env.reset()
    assert isinstance(obs, dict)
    assert isinstance(info, dict)
    # Check step with valid action
    action = Action(agent_idx=0, code="pass", game_state=None)
    obs, reward, terminated, truncated, info = env.step(action)
    assert isinstance(obs, dict)
    assert isinstance(reward, float)
    assert isinstance(terminated, bool)
    assert isinstance(truncated, bool)
    assert isinstance(info, dict)


def test_gym_env_rejects_bad_action(env):
    # Action missing required fields
    with pytest.raises(Exception):
        env.step({"bad": "action"})
    # Action with wrong type
    with pytest.raises(Exception):
        env.step(123)
    # Action with out-of-bounds agent_idx
    with pytest.raises(Exception):
        env.step(Action(agent_idx=99, code="pass", game_state=None))


def test_gym_env_action_space_sample(env):
    sample = env.action_space.sample()
    # Should be a dict with required keys
    assert "agent_idx" in sample
    assert "code" in sample
    assert "game_state" in sample


def test_gym_env_observation_space_sample(env):
    sample = env.observation_space.sample()
    # Should be a dict with required keys
    assert "raw_text" in sample
    assert "entities" in sample
    assert "inventory" in sample
    assert "research" in sample
    assert "game_info" in sample
    assert "score" in sample
    assert "flows" in sample
    assert "task_verification" in sample
    assert "messages" in sample
    assert "serialized_functions" in sample
