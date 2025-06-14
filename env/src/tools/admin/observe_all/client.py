import math
from timeit import default_timer as timer

import numpy as np
from numpy import ndarray, zeros

from env.src.instance import CHUNK_SIZE, MAX_SAMPLES

# from gym.utils import stitch
# from gym.observation_state import FIELDS, ObservationState
from env.src.tools.tool import Tool


class ObserveAll(Tool):
    def __init__(self, connection, game_state: "ObservationState"):
        super().__init__(connection, game_state)
        mu, sigma = 0, CHUNK_SIZE * 20
        self.minimap_normal = np.random.normal(mu, sigma, MAX_SAMPLES)
        self.chunk_cursor = 0

    def __call__(self, trace=False, **kwargs) -> dict:
        """

        -Chunks: At each time t, the agent receives details of a chunks of 32 x 32 tiles sampled from the environment.
        Each chunk contains a density map of resources, enemies, water, player factory.

        -Local Environment: At each time t, the agent receives all entities in a 100 × 100 grid centered on the agent’s position p. Each entity type is
        represented by a unique integer index.

        -Position: At each time t, the agent receives the agent’s current absolute position p.

        -Points of interest: At each time t, the agent receives the relative positions of the nearest points of interest.

        :param trace:
        :param kwargs:
        :return:
        """
        chunk_x, chunk_y, index_x, index_y = self._sample_chunk()
        movement_field_x, movement_field_y = (
            self.game_state.movement_vector[0],
            self.game_state.movement_vector[1],
        )
        omit = kwargs
        response, execution_time = self.execute(
            self.player_index,
            chunk_x,
            chunk_y,
            self.game_state.bounding_box,
            movement_field_x,
            movement_field_y,
            self.game_state.bounding_box * 2,
            trace,
            omit,
        )

        if isinstance(response, str):
            # check that response endswith "attempt to index field 'actions' (a nil value)"
            if response.endswith("attempt to index field 'actions' (a nil value)"):
                raise Exception("No actions available")

        elif response["local_environment"]:
            pass

        if not response:
            return

        try:
            if "chunk" in response:
                self._index_chunk(response["chunk"], index_x, index_y)
        except IndexError as e:
            raise Exception("Cannot move further", str(e.args))

        try:
            if "local_environment" in response:
                self._convert_sparse_local_into_gridworld(
                    response["local_environment"], movement_field_x, movement_field_y
                )
        except IndexError as e:
            raise Exception("Cannot move further", str(e.args))

        try:
            if "points_of_interest" in response:
                points_x, points_y, poi_time = (
                    self._convert_sparse_coordinates_into_tensors(
                        response["points_of_interest"]
                    )
                )
        except IndexError as e:
            raise Exception("Cannot move further", str(e.args))

        try:
            if "distance_to_points_of_interest" in response:
                distance_to_points_of_interest, dpoi_time = (
                    self._convert_sparse_continuous_into_tensor(
                        response["distance_to_points_of_interest"], init=100000
                    )
                )
        except IndexError as e:
            raise Exception("Cannot move further", str(e.args))

        if "buildable" in response:
            buildable, build_time = self._convert_sparse_continuous_into_tensor(
                response["buildable"]
            )

        try:
            if "collision" in response:
                collision_mask = self._collision_mask(response["collision"])
        except IndexError as e:
            raise Exception("Cannot move further", str(e.args))

        if "statistics" in response:
            statistics = response["statistics"]

        if "score" in response:
            score = response["score"]
        # if 'objective' in response:
        #    objective, obj_time = await self._convert_sparse_continuous_into_tensor(response['objective'])

        observation = {
            "local": self.game_state.grid_world,
            "minimap": self.game_state.minimaps,  # Do not do this during observation - it is expensive!
            "compass": np.stack([points_x, points_y], axis=1),
            "buildable": buildable,
            "collision_mask": collision_mask,
            "statistics": statistics,
            "score": score,
        }
        self.last_observation = observation

        return observation

    def _sample_chunk_from_normal(self, player_offset):
        normal = self.minimap_normal[self.chunk_cursor % MAX_SAMPLES]
        offset = normal + player_offset
        self.chunk_cursor += 1
        return offset // CHUNK_SIZE

    def _sample_chunk(self):
        x = self._sample_chunk_from_normal(self.game_state.player_location.x)
        y = self._sample_chunk_from_normal(self.game_state.player_location.y)
        index_x = x + int(self.game_state.minimap_bounding_box / 2)
        index_y = y + int(self.game_state.minimap_bounding_box / 2)

        return int(x), int(y), int(index_x), int(index_y)

    def _convert_sparse_continuous_into_tensor(self, local_counts: dict, init=0):
        start = timer()
        one_hot = np.full((256), init)  # zeros(256)

        for key, value in local_counts.items():
            index = self.game_state.vocabulary._update_vocabulary(key)
            one_hot[index] = value

        return np.reshape(one_hot, one_hot.shape + (1,)), timer() - start

    def _convert_sparse_coordinates_into_tensors(self, local_counts: dict):
        start = timer()
        one_hot_x = zeros(256)
        one_hot_y = zeros(256)
        if not local_counts:
            local_counts = {}
        for key, value in local_counts.items():
            lua_key = key.replace("_", "-")
            index = self.game_state.vocabulary._update_vocabulary(lua_key)
            one_hot_x[index] = value["x"]
            one_hot_y[index] = value["y"]
        end = timer() - start
        return (
            np.reshape(one_hot_x, one_hot_x.shape + (1,)),
            np.reshape(one_hot_y, one_hot_y.shape + (1,)),
            end,
        )

    def _convert_sparse_local_into_gridworld(
        self, local_environment_sparse, new_field_x, new_field_y
    ):
        # print(new_field_x, new_field_y)
        new_field_x = new_field_y = False
        range_x = (
            math.floor(new_field_x) if new_field_x else self.game_state.bounding_box
        )
        range_y = (
            math.floor(abs(new_field_y))
            if new_field_y
            else self.game_state.bounding_box
        )

        try:
            local_environment_dense, elapsed = self._get_dense_environment(
                range_x, range_y, local_environment_sparse
            )
        except IndexError:
            pass

        y, x = np.where(local_environment_dense == -2)

        new_field_y = new_field_y = False
        # If moving vertically
        if new_field_y and not new_field_x:
            local_environment_2d: ndarray = np.reshape(
                local_environment_dense, (-1, self.game_state.bounding_box)
            )
            self.game_state.grid_world = stitch(
                self.game_state.grid_world, local_environment_2d, (0, new_field_y)
            )
        # If moving horizontally
        elif new_field_x and not new_field_y:
            local_environment_2d: ndarray = np.reshape(
                local_environment_dense, (-1, self.game_state.bounding_box)
            )
            self.game_state.grid_world = stitch(
                self.game_state.grid_world, local_environment_2d, (new_field_x, 0)
            )
        else:
            self.game_state.grid_world = np.reshape(
                local_environment_dense, (range_x, range_y)
            )

        # plt.imshow(np.array(self.grid_world, dtype="float"), cmap='gray', interpolation='nearest')
        # plt.show()

    def _index_chunk(self, chunk_map, index_x, index_y):
        if not chunk_map:
            raise Exception("Anonymous error from the server")

        if (
            index_x >= self.game_state.minimap_bounding_box
            or index_y >= self.game_state.minimap_bounding_box
            or index_x < 0
            or index_y < 0
        ):
            return 0
        for type, count in chunk_map.items():
            if count == 0:
                continue
            self.game_state.minimaps[self._get_type_index(type)][index_x, index_y] = (
                count
            )
        return chunk_map

    def _get_type_index(self, type):
        return FIELDS.index(type)

    def _get_dense_environment(self, range_x, range_y, local_environment_sparse):
        local_environment_dense = []
        start = timer()

        dense_array = np.full((range_y, range_x), -1, dtype=object)

        # Populate the dense array using the sparse dictionary
        for key, value in local_environment_sparse.items():
            if key > range_y * range_x:
                break

            row = math.floor(key // range_y)
            col = math.floor(key % range_y)
            if (
                row >= self.game_state.bounding_box
                or col >= self.game_state.bounding_box
                or row < 0
                or col < 0
            ):
                continue
            dense_array[row, col] = self.game_state.vocabulary._update_vocabulary(value)
        end = timer()
        diff = end - start

        return dense_array, diff

    def _collision_mask(self, sparse_collision_mask):
        bounding_box = self.game_state.bounding_box
        dense_array = np.full((bounding_box, bounding_box), 1, dtype=object)

        # Populate the dense array using the sparse dictionary
        for key, value in sparse_collision_mask.items():
            # key = key - (self.bounding_box)*(self.bounding_box/2)
            col = math.floor((key // bounding_box)) - self.game_state.player_location[1]
            row = math.floor((key % bounding_box)) - self.game_state.player_location[0]
            if row >= bounding_box or col >= bounding_box or col <= 0 or row <= 0:
                pass
            try:
                dense_array[col, row] = value
            except Exception:
                pass

        # plt.imshow(np.array(dense_array, dtype="float"), cmap='gray', interpolation='nearest')
        # plt.show()
        # dense_array = np.flipud(dense_array)
        self.game_state.collision_mask = dense_array
        return dense_array
