from abc import ABC, abstractmethod
from typing import Optional

from search.mcts.db_client import DBClient
from search.model.program import Program


class DBSampler(ABC):

    def __init__(self, db_client: DBClient, maximum_lookback=10):
        self.db_client = db_client
        self.maximum_lookback = maximum_lookback


    @abstractmethod
    async def sample_parent(self, version=1, **kwargs) -> Optional[Program]:
        pass