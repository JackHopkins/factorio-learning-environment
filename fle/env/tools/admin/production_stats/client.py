from typing import Dict

from fle.env.tools import Tool


class ProductionStats(Tool):
    def __init__(self, lua_script_manager, game_state):
        self.state = {"input": {}, "output": {}}
        super().__init__(lua_script_manager, game_state)

    def __call__(self) -> Dict[str, Dict[str, int]]:
        """
        Gets the difference in production statistics since the last measurement.
        Returns a dictionary of item names to net production/consumption counts.
        """

        result, _ = self.execute(self.player_index)

        if isinstance(result, str):
            raise Exception(result)

        result = self.clean_response(result)

        # Calculate the difference in production statistics
        input_diff = {}
        for item, count in result["input"].items():
            input_diff[item] = count - self.state["input"].get(item, 0)

        output_diff = {}
        for item, count in result["output"].items():
            output_diff[item] = count - self.state["output"].get(item, 0)

        self.state = result

        return {"input": input_diff, "output": output_diff}

    def reset_production_stats(self):
        """Resets the production statistics to current values"""
        lua_command = """
        local scores = production_score.get_production_scores()
        global.initial_score = scores
        return true
        """
        self.execute(lua_command)
