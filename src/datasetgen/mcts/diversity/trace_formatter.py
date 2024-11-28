from dataclasses import dataclass
from typing import List, Dict, Optional
import json
from pathlib import Path

from datasetgen.mcts.diversity.trace import Trace


@dataclass
class GPTMessage:
    role: str
    content: str


@dataclass
class GPTConversation:
    messages: List[GPTMessage]


class TraceFormatter:
    def __init__(self, system_prompt: str = "You are a helpful AI assistant that writes Python code.", formatter=None):
        self.system_prompt = system_prompt
        self.formatter = formatter

    def format_trace(self, programs: Dict[int, Dict], trace: Trace) -> Optional[GPTConversation]:
        """Convert a single trace into a GPT conversation format"""
        messages = []

        # Add system message
        messages.append(GPTMessage(role="system", content=self.system_prompt))

        # Process each program in the trace
        for i, prog_id in enumerate(trace.programs):
            prog = programs[prog_id]

            # Extract user message and assistant response
            # Assuming the response field contains the full conversation
            try:
                # Add assistant message
                if 'code' in prog:
                    messages.append(GPTMessage(
                        role="assistant",
                        content=self.formatter.summarize_code_block(prog['code']) if i < len(trace.programs) - 1 else prog['code']
                    ))

                # Add user message
                if 'response' in prog and i != len(trace.programs) - 1:  # Exclude last user message
                    messages.append(GPTMessage(
                        role="user",
                        content=f"Execution result:\n{prog['response']}"
                    ))

            except (json.JSONDecodeError, KeyError) as e:
                print(f"Error processing program {prog_id}: {e}")
                return None

        return GPTConversation(messages=messages)

    def format_traces(self, programs: Dict[int, Dict], traces: List[List[int]], output_dir: Path, filename="gpt_training_data_masked") -> None:
        """Convert all traces to GPT format and save them"""
        output_dir.mkdir(parents=True, exist_ok=True)

        formatted_conversations = []

        for i, trace in enumerate(traces):
            conversation = self.format_trace(programs, trace)
            if conversation:
                # Convert to JSONL format
                conv_dict = {
                    "messages": [
                        {"role": msg.role, "content": msg.content}
                        for msg in conversation.messages
                    ]
                }
                formatted_conversations.append(conv_dict)

        # Save all conversations to a JSONL file
        output_file = output_dir / f"{filename}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for conv in formatted_conversations:
                f.write(json.dumps(conv) + '\n')

        print(f"Saved {len(formatted_conversations)} conversations to {output_file}")


def save_selected_traces(programs: Dict[int, Dict],
                         selected_traces: List['Trace'],
                         output_dir: Path,
                         system_prompt: str = "You are a helpful AI assistant that writes Python code.") -> None:
    """Helper function to save selected traces in GPT format"""
    formatter = TraceFormatter(system_prompt=system_prompt)

    # Convert Trace objects to lists of program IDs
    trace_programs = [trace.programs for trace in selected_traces]

    # Format and save the traces
    formatter.format_traces(programs, trace_programs, output_dir)