from typing import Optional

import tenacity
from tenacity import retry_if_exception_type, wait_exponential

from fle.agents.llm.parsing import Policy
from fle.agents.agent_abc import AgentABC
from fle.agents.basic_agent import FINAL_INSTRUCTION, GENERAL_INSTRUCTIONS
from fle.agents.formatters import RecursiveReportFormatter
from fle.agents.models import CompletionResult, Response
from fle.commons.models.conversation import Conversation
from fle.commons.models.generation_parameters import GenerationParameters
from fle.env import Layer, Position
from fle.env.namespace import FactorioNamespace

from fle.agents.llm.api_factory import APIFactory
from fle.agents.llm.parsing import parse_response

VISUAL_INSTRUCTIONS = """
## Visual Information
For each step, you will be provided with a visual representation of the current game state.
This image shows:
- The player's position (crosshair marker)
- Existing entities and their orientation
- Resources, water, and terrain features
- Spatial relationships between elements
- A legend showing the shapes and colours of each entity

Use this visual information to:
- Plan efficient factory layouts
- Verify entity placement
- Identify resource locations
- Guide navigation decisions
- Diagnose issues with automation

Correlate what you see in the image with the textual output from your code to make better decisions.
"""


class VisualAgent(AgentABC):
    """
    An agent that renders the Factorio map at each step to provide visual context.
    """

    def __init__(self, model, system_prompt, task, render_radius=20, *args, **kwargs):
        """
        Initialize the Visual Agent.

        Args:
            model: The LLM model to use
            system_prompt: System prompt for the agent
            task: The task to perform
            render_radius: Radius around player to render (default: 20)
        """
        # Initialize the base agent
        instructions = (
            GENERAL_INSTRUCTIONS
            + system_prompt
            + FINAL_INSTRUCTION
            + VISUAL_INSTRUCTIONS
        )
        self.task = task
        instructions += f"\n\n### Goal\n{task.goal_description}\n\n"

        super().__init__(model, instructions, *args, **kwargs)

        self.render_radius = render_radius
        self.api_factory = APIFactory(model)
        self.formatter = RecursiveReportFormatter(
            chunk_size=16,
            llm_call=self.api_factory.acall,
            cache_dir=".fle/summary_cache",
        )
        self.generation_params = GenerationParameters(n=1, max_tokens=2048, model=model)
        self.last_image_base64 = None

    async def step(
        self,
        conversation: Conversation,
        response: Response,
        namespace: FactorioNamespace,
    ) -> Policy:
        """
        Execute a step in the agent's process, rendering the map and incorporating it into the prompt.

        Args:
            conversation: Current conversation state
            response: Last response from the environment
            namespace: Current namespace with variables and functions

        Returns:
            Policy: Next actions to execute
        """
        try:
            # Render the current map state
            render_image = await self._render_map(namespace)

            # Format the base conversation
            formatted_conversation = await self.formatter.format_conversation(
                conversation, namespace
            )

            # Add the rendered image to the latest user message if we have one
            if render_image and len(formatted_conversation.messages) > 0:
                # Find the last user message
                for i in range(len(formatted_conversation.messages) - 1, -1, -1):
                    if formatted_conversation.messages[i].role == "user":
                        # Replace the simple text content with multimodal content
                        original_content = formatted_conversation.messages[i].content

                        # Create multimodal content with both text and image
                        formatted_conversation.messages[i].content = [
                            {"type": "text", "text": original_content},
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": render_image,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"[Current map view (radius: {self.render_radius}) - Use this visual information to guide your decisions. Be sure to reference to legend to understand what each entity is.]",
                            },
                        ]
                        break

            # Set the new conversation state for external use
            self.set_conversation(formatted_conversation)

            # Get the next policy
            return await self._get_policy(formatted_conversation)

        except Exception as e:
            print(f"Error in visual agent step: {str(e)}")
            # Fall back to basic approach if rendering fails
            formatted_conversation = await self.formatter.format_conversation(
                conversation, namespace
            )
            self.set_conversation(formatted_conversation)
            return await self._get_policy(formatted_conversation)

    async def _render_map(self, namespace: FactorioNamespace) -> Optional[str]:
        """
        Render the current map state and convert to base64.

        Args:
            namespace: Current namespace with game state

        Returns:
            str: Base64-encoded image or None if rendering fails
        """
        try:
            # Get player position (or use 0,0 if not available)
            player_pos = Position(0, 0)
            if hasattr(namespace, "PLAYER") and hasattr(namespace.PLAYER, "position"):
                player_pos = namespace.PLAYER.position
            elif hasattr(namespace, "player_location"):
                player_pos = namespace.player_location

            # Render around player position
            render = namespace._render(
                position=player_pos,
                layers=Layer.ALL,  # Render all layers for complete information
            )

            # Convert image to base64 for embedding
            self.last_image_base64 = render.to_base64()
            # render.show()
            return self.last_image_base64

        except Exception as e:
            print(f"Error rendering map: {str(e)}")
            return None

    @tenacity.retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_exponential(multiplier=1, min=4, max=10),
    )
    async def _get_policy(self, conversation: Conversation):
        """
        Get the next policy from the LLM.

        Args:
            conversation: Current conversation state

        Returns:
            Policy: Next actions to execute
        """
        response = await self.api_factory.acall(
            messages=self.formatter.to_llm_messages(conversation),
            n_samples=1,
            temperature=self.generation_params.temperature,
            max_tokens=self.generation_params.max_tokens,
            model=self.generation_params.model,
        )

        policy = parse_response(response)
        if not policy:
            raise Exception("Not a valid Python policy")

        return policy

    async def end(self, conversation: Conversation, completion: CompletionResult):
        """
        Cleanup when a trajectory ends.

        Args:
            conversation: Final conversation state
            completion: Completion result
        """
        # Additional cleanup if needed
        pass
