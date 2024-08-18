import gym
import numpy as np
from gym import spaces

HEIGHT = 100
WIDTH = 100
N_CHANNELS = 3
N_DISCRETE_ACTIONS = 5

class FactorioEnv(gym.Env):
  """Custom Environment that follows gym interface"""
  metadata = {'render.modes': ['human']}


  def __init__(self, arg1, arg2):
    super(FactorioEnv, self).__init__()

    # Define action and observation space
    # They must be gym.spaces objects
    # Example when using discrete actions:
    self.action_space = spaces.Discrete(N_DISCRETE_ACTIONS)
    # Example for using image as input:
    self.observation_space = spaces.Box(low=0, high=255, shape=(HEIGHT, WIDTH, N_CHANNELS), dtype=np.uint8)

  def step(self, action):
    # Execute one time step within the environment
    pass

  def reset(self):
    # Reset the state of the environment to an initial state
    pass

  def render(self, mode='human', close=False):
    # Render the environment to the screen
    pass


  def close(self):
    pass