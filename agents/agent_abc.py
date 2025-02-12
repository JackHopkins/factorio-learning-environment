from agents import Response, Python, CompletionResult
from models.conversation import Conversation


class AgentABC:
   model: str

   def __init__(self, model, *args, **kwargs):
       self.model = model

   def set_conversation(self, conversation: Conversation) -> None:
       pass

   async def step(self, conversation: Conversation, response: Response) -> Python:
       pass

   async def end(self, conversation: Conversation, completion: CompletionResult):
       pass


