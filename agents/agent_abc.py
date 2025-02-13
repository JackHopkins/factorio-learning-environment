from agents import Response, Python, CompletionResult
from models.conversation import Conversation


class AgentABC:
   model: str
   conversation: Conversation

   def __init__(self, model, *args, **kwargs):
       self.model = model

   def set_conversation(self, conversation: Conversation) -> None:
       self.conversation = conversation

   async def step(self, conversation: Conversation, response: Response) -> Python:
       pass

   async def end(self, conversation: Conversation, completion: CompletionResult):
       pass


