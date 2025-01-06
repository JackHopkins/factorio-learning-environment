from abc import ABC, abstractmethod
from typing import Optional

from fontTools.ttLib.ttVisitor import visit
from psycopg2.extras import DictCursor

from search.mcts.db_client import DBClient
from search.model.program import Program


class DBSampler(ABC):

    def __init__(self, db_client: DBClient, maximum_lookback=10):
        self.db_client = db_client
        self.maximum_lookback = maximum_lookback


    @abstractmethod
    async def sample_parent(self, version=1, **kwargs) -> Optional[Program]:
        pass

    async def visit(self, id, children=1):
        """
        Increments the visit count for a given program ID in the database.
        Args:
            id: The ID of the program to increment the visit count for.
            count: The number of times to increment the visit count. Defaults to 1.
        """
        assert children > 0
        with self.db_client.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # Get visit count from the database.
                cur.execute("SELECT visits FROM programs WHERE id = %s", (id,))
                visits = cur.fetchone()['visits']

                # If the visit count is None, return
                if visits is None:
                    return

                # Update the program ID to increase the visit count by the specified amount.
                cur.execute("UPDATE programs SET visits = visits + %s WHERE id = %s", (visits+children, id))