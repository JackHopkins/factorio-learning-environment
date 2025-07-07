from fle.env.entities import Entity, Inventory, Position
from fle.env.tools import Tool


class Print(Tool):
    def __init__(self, connection, game_state):
        super().__init__(connection, game_state)

    def load(self):
        pass

    def __call__(self, *args):
        """
        Adds a string to stdout
        :param args:
        :return:
        """
        responses = []
        for message in args:
            if (
                isinstance(message, Entity)
                or isinstance(message, Inventory)
                or isinstance(message, dict)
                or isinstance(message, bool)
                or isinstance(message, str)
                or isinstance(message, Position)
                or isinstance(message, list)
                or isinstance(message, tuple)
            ):
                responses.append(str(message))
            # Elif message extends 'BaseModel' (i.e. is a 'Position' or 'Entity')
            elif hasattr(message, "dict"):
                responses.append(str(message.dict()))
            else:
                response, elapsed = self.execute(message)
                responses.append(response)
                if not response:
                    raise Exception("Could not print", response)
        response = "\t".join(responses).lstrip("\t")

        return response
