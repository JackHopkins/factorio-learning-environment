from instance import PLAYER
from tools.tool import Tool


class RegenerateResources(Tool):

    def __init__(self, *args):
        super().__init__(*args)

    def __call__(self) -> bool:
        """
        Fills up all resources on the map back to full
        """
        self.execute(PLAYER)

        return True