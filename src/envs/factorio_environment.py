from typing import Optional, Tuple

import gym
from gym.envs.registration import register
import numpy as np
from gym import spaces
from numpy import zeros

from src.factorio_instance import FactorioInstance
from src.main import Vocabulary

PLAYER = 1
NONE = 'nil'
CHUNK_SIZE = 32
MAX_SAMPLES = 5000

class FactorioEnv(gym.Env, FactorioInstance):
    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 4}

    def __init__(self,
                 address: str = None,
                 vocabulary: Vocabulary = None,
                 bounding_box=100,
                 tcp_port=27000,
                 render_mode: Optional[str] = None,
                 inventory: dict = {}):

        assert render_mode is None or render_mode in self.metadata["render_modes"]

        super(FactorioEnv, self).__init__(address=address,
                                          vocabulary=vocabulary,
                                          bounding_box=bounding_box,
                                          tcp_port=tcp_port,
                                          inventory=inventory)

        self.window_size = 512
        self.inventory = inventory

        mu, sigma = 0, CHUNK_SIZE * 20
        self.minimap_normal = s = np.random.normal(mu, sigma, MAX_SAMPLES)
        self.chunk_cursor = 0
        #self.minimaps: spaces.Dict = self._initialise_minimaps()

        # Observations are dictionaries with the agent's and the target's location.
        # Each location is encoded as an element of {0, ..., `size`}^2, i.e. MultiDiscrete([size, size]).
        # We have 4 actions, corresponding to "right", "up", "left", "down"
        self.action_space = spaces.MultiDiscrete([5, 4, 256])

        """
        If human-rendering is used, `self.window` will be a reference
        to the window that we draw to. `self.clock` will be a clock that is used
        to ensure that the environment is rendered at the correct framerate in
        human-mode.
        """
        if render_mode == "human":
            import pygame  # import here to avoid pygame dependency with no render

            pygame.init()
            pygame.display.init()
            self.window = pygame.display.set_mode((self.window_size, self.window_size))
            self.clock = pygame.time.Clock()

        # The following line uses the util class Renderer to gather a collection of frames
        # using a method that computes a single frame. We will define _render_frame below.
        # self.renderer = Renderer(render_mode, self._render_frame)
        self.observation_space = spaces.Dict({
            'local': spaces.Box(0, 256, shape=(self.bounding_box, self.bounding_box), dtype=int),
            'minimap': spaces.Box(0, 32*32, shape=(12,self.bounding_box*4, self.bounding_box*4), dtype=int),
            #'compass': spaces.Box(0, 32*32, shape=(12,self.bounding_box*4, self.bounding_box*4), dtype=int),
        })

        #self.action_space = spaces.Discrete(4)

    def reset(
        self,
        *,
        seed: Optional[int] = None,
        return_info: bool = False,
        options: Optional[dict] = None,
    ):
        #super().reset()
        # We need the following line to seed self.np_random
        #super().reset()
        observation = self.initialise(**self.inventory)
        #self.renderer.reset()
        #self.renderer.render_step()
        return observation

    def _get_obs(self):
        return self.observe(trace=True)

    def _get_info(self):
        return {}

    def _get_reward(self):
        return

    def step(self, action_tuple: Tuple[int,int,int]):
        action, direction, entity_index = action_tuple
        entity = self.vocabulary.i_vocabulary[entity_index] if entity_index in self.vocabulary.i_vocabulary else None
        if action == 0:
            self.move(direction)
        elif action == 1 and entity:
            self.place_entity(entity, direction)
        elif action == 2 and entity:
            self.trail(entity)
        elif action == 3:
            self.insert_item()
        elif action == 4:
            self.interact()


        # An episode is done if the agent has reached the target
        done = False
        #reward = 1 if done else 0  # Binary sparse rewards
        observation = self._get_obs()
        reward = self._get_reward()
        info = self._get_info()

        # add a frame to the render collection
        #self.renderer.render_step()

        return observation, reward, done, info

    def render(self):
        return self.renderer.get_renders()

    def _render_frame(self, mode: str):
        import pygame  # avoid global pygame dependency. This method is not called with no-render.

        canvas = pygame.Surface((self.window_size, self.window_size))
        canvas.fill((255, 255, 255))
        pix_square_size = (
                self.window_size / self.size
        )  # The size of a single grid square in pixels

        # First we draw the target
        pygame.draw.rect(
            canvas,
            (255, 0, 0),
            pygame.Rect(
                pix_square_size * self._target_location,
                (pix_square_size, pix_square_size),
            ),
        )
        # Now we draw the agent
        pygame.draw.circle(
            canvas,
            (0, 0, 255),
            (self._agent_location + 0.5) * pix_square_size,
            pix_square_size / 3,
        )

        # Finally, add some gridlines
        for x in range(self.size + 1):
            pygame.draw.line(
                canvas,
                0,
                (0, pix_square_size * x),
                (self.window_size, pix_square_size * x),
                width=3,
            )
            pygame.draw.line(
                canvas,
                0,
                (pix_square_size * x, 0),
                (pix_square_size * x, self.window_size),
                width=3,
            )

        if mode == "human":
            assert self.window is not None
            # The following line copies our drawings from `canvas` to the visible window
            self.window.blit(canvas, canvas.get_rect())
            pygame.event.pump()
            pygame.display.update()

            # We need to ensure that human-rendering occurs at the predefined framerate.
            # The following line will automatically add a delay to keep the framerate stable.
            self.clock.tick(self.metadata["render_fps"])
        else:  # rgb_array
            return np.transpose(
                np.array(pygame.surfarray.pixels3d(canvas)), axes=(1, 0, 2)
            )

    def close(self):
        if self.window_size is not None:
            import pygame

            try:
                pygame.display.quit()
                pygame.quit()
            except:
                pass

if hasattr(__loader__, 'name'):
  module_path = __loader__.name
elif hasattr(__loader__, 'fullname'):
  module_path = __loader__.fullname

register(
    id='Factorio-v0',
    entry_point=module_path + ':FactorioEnv',
    max_episode_steps=15000,
)
