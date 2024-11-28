from typing import List

from datasetgen.mcts.conversation_formatter import CodeProcessor
from datasetgen.mcts.diversity.extractor.trace_extractor import TraceExtractor


class ReasoningExtractor(TraceExtractor):

    def __init__(self, programs):
        super().__init__(programs)
        self.formatter = CodeProcessor()

    def extract_from_trace(self, trace: List[int]) -> str:
        """Convert trace to string for encoding"""
        text = " ".join(self.formatter.summarize_code_block(self.programs[pid]['code']) if self.programs[pid]['code'] else '' for pid in trace)

        return text