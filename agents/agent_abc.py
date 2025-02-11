from agents import Response, Python, CompletionResult
from eval.open.model.conversation import Conversation


class AgentABC:
   def __init__(self, *args, **kwargs):
       pass
   def set_conversation(self, conversation: Conversation) -> None:
       pass
   def step(self, conversation: Conversation, response: Response) -> Python:
       pass
   def end(self, conversation: Conversation, completion: CompletionResult):
       pass


