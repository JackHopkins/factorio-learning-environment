from fle.env.tools import Tool
import json


class Reset(Tool):
	def __init__(self, connection, game_state):
		super().__init__(connection, game_state)

	def __call__(
		self,
		inventories=None,
		reset_position=False,
		all_technologies_researched=True,
		clear_entities=True,
	):
		"""
		Reset the Factorio game state via Lua action, mirroring FactorioInstance.reset/_reset.

		Args:
			inventories (list[dict]|dict|None): Either a list indexed by agent (1-based in Lua)
			    or a dict keyed by agent index (int or str) mapping to {item_name: count}.
			reset_position (bool): If True, teleport agents to spawn offsets.
			all_technologies_researched (bool): If True, research all technologies; else reset force.
		"""
		if inventories is None:
			inventories = {}
		# Encode to JSON string for Lua
		inventories_json = json.dumps(inventories)

		reset_position = str(reset_position).lower()
		all_technologies_researched = str(all_technologies_researched).lower()
		clear_entities = str(clear_entities).lower()

		response, _ = self.execute(
			inventories_json,
			reset_position,
			all_technologies_researched,
			clear_entities,
		)
		return response

