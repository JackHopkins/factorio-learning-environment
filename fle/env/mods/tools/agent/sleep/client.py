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
        # Get initial tick
        ticks_elapsed = 0
        start_tick, _ = self.execute(-1)
        target_ticks = seconds * 60  # Convert seconds to ticks (60 ticks = 1 second)

        while True:
            current_tick, _ = self.execute(ticks_elapsed)
            ticks_elapsed = current_tick - start_tick

            if ticks_elapsed >= target_ticks:
                return True

            # Sleep for a small interval to prevent excessive polling
            # Using 0.05 seconds (50ms) as a reasonable polling interval
            sleep(0.05)
