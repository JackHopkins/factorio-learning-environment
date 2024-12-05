from abc import ABC, abstractmethod
from typing import Optional

from datasetgen.mcts.db_client import DBClient
from datasetgen.mcts.model.program import Program


class DBSampler(ABC):

    def __init__(self, db_client: DBClient):
        self.db_client = db_client


    @abstractmethod
    async def sample_parent(self, version=1, **kwargs) -> Optional[Program]:
        pass