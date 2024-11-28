from typing import List

from datasetgen.mcts.diversity.extractor.trace_extractor import TraceExtractor


class CodeExtractor(TraceExtractor):

    def __init__(self, programs):
        super().__init__(programs)

    def extract_from_trace(self, trace: List[int]) -> str:
        """Convert trace to string for encoding"""
        #text = " ".join(self.programs[pid]['code'] if self.programs[pid]['code'] else '' for pid in trace)
        text = self.programs[trace[-1]]['code']
        return text