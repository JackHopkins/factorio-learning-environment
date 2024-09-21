import math

from controllers._action import Action
from controllers.get_path import GetPath
from controllers.observe_all import ObserveAll
from controllers.request_path import RequestPath
from factorio_entities import Position
from factorio_instance import PLAYER, NONE
from factorio_types import Prototype


class MoveTo(Action):

    def __init__(self, connection, game_state):
        self.game_state = game_state
        super().__init__(connection, game_state)
        self.observe = ObserveAll(connection, game_state)
        self.request_path = RequestPath(connection, game_state)
        self.get_path = GetPath(connection, game_state)

    def __call__(self, position: Position, laying: Prototype = None, leading: Prototype = None) -> bool:
        """
        Move to a position.
        :param position: Position to move to.
        :param laying: Entity to lay down behind you as you move. e.g. 'Prototype.TransportBelt', facing away from you.
        :param leading: Entity to lay down in front of you as you move. e.g. 'Prototype.TransportBelt', facing towards you.
        :example move_to(nearest(Prototype.StoneFurnace), laying=Prototype.TransportBelt)
        :return:
        """
        X_OFFSET, Y_OFFSET = 0.5, 0

        x, y = math.floor(position.x*4)/4 + X_OFFSET, math.floor(position.y*4)/4 + Y_OFFSET
        nposition = Position(x=x, y=y)
        print(f"Moving to {x}, {y}")
        path_handle = self.request_path(start=Position(x=self.game_state.player_location[0],
                                                       y=self.game_state.player_location[1]), finish=nposition,
                                        allow_paths_through_own_entities=True)
        try:
            if laying is not None:
                entity_name = laying.value[0]
                response, execution_time = self.execute(PLAYER, path_handle, entity_name, 1)
            elif leading:
                entity_name = leading.value[0]
                response, execution_time = self.execute(PLAYER, path_handle, entity_name, 0)
            else:
                response, execution_time = self.execute(PLAYER, path_handle, NONE, NONE)

            if isinstance(response, int) and response == 0:
                raise Exception("Could not move.")

            if response == 'trailing' or response == 'leading':
                raise Exception("Could not lay entity, perhaps a typo?")

            if response and isinstance(response, dict):
                self.game_state.player_location = (response['x'], response['y'])

            return response, execution_time
        except Exception as e:
            raise Exception(f"Cannot move. {e}")
    #
    # def _move2(self, x: int, y: int, laying=None, leading=None) -> bool:
    #     """
    #     The agent moves in a cardinal direction.
    #     :param direction: Index between (0,3) inclusive.
    #     :return: Whether the movement was carried out.
    #     """
    #     try:
    #         last_location = self.game_state.player_location
    #         if laying:
    #             response, execution_time = self.execute(PLAYER, x, y, laying, 1)
    #         elif leading:
    #             response, execution_time = self.execute(PLAYER, x, y, leading, 0)
    #         else:
    #             response, execution_time = self.execute(PLAYER, x, y, NONE, NONE)
    #
    #         if isinstance(response, int) and response == 0:
    #             raise Exception("Could not move.")
    #
    #         if response == 'trailing' or response == 'leading':
    #             raise Exception("Could not lay entity, perhaps a typo?")
    #
    #         if response and isinstance(response, dict):
    #             self.game_state.player_location = (response['x'], response['y'])
    #             movement_vector = (self.game_state.player_location[0] - last_location[0],
    #                                self.game_state.player_location[1] - last_location[1])
    #
    #             self.last_observed_player_location = (self.game_state.last_observed_player_location[0] + movement_vector[0],
    #                                                   self.game_state.last_observed_player_location[1] + movement_vector[1])
    #         return response, execution_time
    #     except Exception as e:
    #         raise Exception(f"Cannot move. {e}")
    #
    # def __call(self,
    #              position: Position = Position(x=0, y=0),
    #              #absolute_position: Optional[Tuple[int, int]],
    #              #relative_position: Tuple[int, int] = (0, 0),
    #              laying=None,
    #              leading=None,
    #              #**kwargs
    #              ):
    #     """
    #     Move to a position.
    #     :param position: Position to move to.
    #     :param laying: Entity to lay down behind you as you move. e.g. 'Prototype.TransportBelt', facing away from you.
    #     :param leading: Entity to lay down in front of you as you move. e.g. 'Prototype.TransportBelt', facing towards you.
    #     :example move_to(nearest(Prototype.StoneFurnace), laying=Prototype.TransportBelt)
    #     :return:
    #     """
    #     if not position:
    #         raise Exception("You need to pass in a position to move to.", position)
    #
    #     if laying != None:
    #         pass
    #
    #     max_attempts = 1
    #     current_attempt = 0
    #     while current_attempt < max_attempts:
    #         try:
    #             relative_position = (0, 0)
    #
    #             if position is not None:
    #                 if not isinstance(position, Position):
    #                     raise Exception(
    #                         f"You need to pass in a Position object. You passed in the following: {str(position)}.")
    #                 #self.observe()
    #
    #             if not isinstance(relative_position, Tuple):
    #                 raise Exception(
    #                     f"You need to pass in a tuple like (x, y). You passed in the following: {str(relative_position)}")
    #
    #             self.follow_path(position, laying=laying, leading=leading)
    #             return
    #         except Exception as e:
    #             current_attempt += 1
    #             if current_attempt == max_attempts:
    #                 raise Exception(f"Could not move_to. {e}")
    #             self.observe()
    #
    # def follow_path(self, end_position, laying=None, leading=None):
    #     #relative_end_x, relative_end_y = relative_position
    #     start_x, start_y = self.game_state.player_location
    #     # offset_x = self.game_state.bounding_box // 2
    #     # offset_y = self.game_state.bounding_box // 2
    #     # end = (offset_x + end_position.x,  # - last_observed_x,
    #     #        offset_y + end_position.y)  # - last_observed_y)
    #     # start = (offset_x + start_x,
    #     #          offset_y + start_y)
    #     # path: ndarray = get_path(end, self.game_state.collision_mask, start=start)
    #     # # Remove the offset from the path
    #     # path = path - [offset_x, offset_y]
    #
    #     handle = self.request_path(start=Position(x=start_x, y=start_y), finish=end_position)
    #     # path: List[Position] = self.get_path(handle)
    #     task_queue = []
    #     task_queue.extend(
    #          [
    #              (lambda s: self._move(position, laying=laying, leading=leading))(position)
    #              for position in path
    #          ]
    #     )
    #     #task_queue.extend([(lambda: self.observe())()])
    #     x_distance = self.game_state.player_location[0] - end_position.x
    #     y_distance = self.game_state.player_location[1] - end_position.y
    #     distance = math.sqrt(x_distance ** 2 + y_distance ** 2)
    #     if distance > 1:
    #         raise Exception(f"Did not arrive at {end_position}. Instead arrived at {self.game_state.player_location}.")
    #     #if (math.floor(self.game_state.player_location[0]*2)/2 != math.floor(position.x*2)/2 or
    #     #        math.floor(self.game_state.player_location[1]*2)/2 != math.floor(position.y*2)/2):
    #     #    raise Exception(f"Did not arrive at {position}. Instead arrived at {self.game_state.player_location}.")
