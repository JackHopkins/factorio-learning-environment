from agents import Response, Python, CompletionResult
from agents.agent_abc import AgentABC
from agents.utils.formatters.recursive_report_formatter import RecursiveReportFormatter
from agents.utils.llm_factory import LLMFactory
from models.conversation import Conversation
from models.generation_parameters import GenerationParameters


class ExampleAgent(AgentABC):
   def __init__(self, model, system_prompt, *args, **kwargs):
       super().__init__( model,*args, **kwargs)
       self.system_prompt = system_prompt
       self.llm_factory = LLMFactory(model)
       self.formatter = RecursiveReportFormatter(
           chunk_size=32,
           llm_call=self.llm_factory.acall,
           cache_dir='summary_cache',
       )
       self.generation_params = GenerationParameters(
           n=1,
           presence_penalty=0.7,
           max_tokens=2048,
           model=model
       )

   def set_conversation(self, conversation: Conversation) -> None:
       pass

   async def step(self, conversation: Conversation, response: Response) -> Python:
       formatted = await self.formatter.format_conversation(conversation)
       formatted_messages = self.formatter.to_llm_messages(formatted)

       response = await self.llm_factory.acall(
           messages=formatted_messages,
           n_samples=1,  # We only need one program per iteration
           temperature=self.generation_params.temperature,
           max_tokens=self.generation_params.max_tokens,
           model=self.generation_params.model,
           presence_penalty=0.7
       )
       return response

   async def end(self, conversation: Conversation, completion: CompletionResult):
       pass


