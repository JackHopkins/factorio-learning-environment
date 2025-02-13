from agents import Response, Python, CompletionResult, Policy
from models.conversation import Conversation


class AgentABC:
   model: str
   system_prompt: str
   conversation: Conversation

   def __init__(self, model, system_prompt, *args, **kwargs):
       self.model = model
       self.system_prompt = system_prompt

   def set_conversation(self, conversation: Conversation) -> None:
       self.conversation = conversation

   async def step(self, conversation: Conversation, response: Response) -> Policy:
       pass

   async def end(self, conversation: Conversation, completion: CompletionResult):
       pass


