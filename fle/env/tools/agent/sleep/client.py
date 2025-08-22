from time import sleep

from fle.env.tools import Tool


class Sleep(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def __call__(self, seconds: int) -> bool:
        """
        Sleep for up to 15 seconds before continuing. Useful for waiting for actions to complete.
        :param seconds: Number of seconds to sleep.
        :return: True if sleep was successful.
        """
        # Track elapsed ticks for appropriate sleep calculation
        ticks_before = self.game_state.instance.get_elapsed_ticks()

        # Update elapsed ticks on server
        _, _ = self.execute(seconds)

        # Sleep for the appropriate real-world time based on elapsed ticks
        ticks_after = self.game_state.instance.get_elapsed_ticks()
        ticks_added = ticks_after - ticks_before
        if ticks_added > 0:
            game_speed = self.game_state.instance.get_speed()
            real_world_sleep = ticks_added / 60 / game_speed if game_speed > 0 else 0
            print(
                f"sleep: Sleeping for {real_world_sleep:.3f} seconds ({ticks_added} ticks at speed {game_speed}x)"
            )
            sleep(real_world_sleep)

        return True
