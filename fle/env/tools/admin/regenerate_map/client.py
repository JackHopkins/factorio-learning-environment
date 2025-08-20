from fle.env.tools import Tool


class RegenerateMap(Tool):
    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self) -> bool:
        """
        Regenerates the map with autoplace and crash-site.
        """
        self.execute(self.player_index)

        return True
