from agents import Response, CompletionResult, Policy
from agents.agent_abc import AgentABC
from agents.utils.formatters.recursive_report_formatter import RecursiveReportFormatter
from agents.utils.llm_factory import LLMFactory
from agents.utils.parse_response import parse_response
from models.conversation import Conversation
from models.generation_parameters import GenerationParameters


class BasicAgent(AgentABC):
   def __init__(self, model, system_prompt, *args, **kwargs):
       super().__init__( model,system_prompt, *args, **kwargs)
       self.system_prompt = system_prompt
       self.llm_factory = LLMFactory(model)
       self.formatter = RecursiveReportFormatter(chunk_size=32,llm_call=self.llm_factory.acall,cache_dir='summary_cache')
       self.generation_params = GenerationParameters(n=1, presence_penalty=0.7, max_tokens=2048, model=model)

   async def step(self, conversation: Conversation, response: Response) -> Policy:
       # We format the conversation every N steps to add a context summary to the system prompt
       formatted_conversation = await self.formatter.format_conversation(conversation)
       # We set the new conversation state for external use
       self.set_conversation(formatted_conversation)

       response = await self.llm_factory.acall(
           messages=self.formatter.to_llm_messages(formatted_conversation.messages),
           n_samples=1,  # We only need one program per iteration
           temperature=self.generation_params.temperature,
           max_tokens=self.generation_params.max_tokens,
           model=self.generation_params.model,
           presence_penalty=0.7
       )

       policy = parse_response(response)
       return policy

   async def end(self, conversation: Conversation, completion: CompletionResult):
       pass


