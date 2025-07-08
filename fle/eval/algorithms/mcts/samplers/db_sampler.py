from abc import ABC, abstractmethod
from typing import Optional

from psycopg2.extras import DictCursor

from fle.commons.db_client import DBClient
from fle.commons.models.program import Program


class DBSampler(ABC):
    def __init__(self, db_client: DBClient, maximum_lookback=10):
        self.db_client = db_client
        self.maximum_lookback = maximum_lookback

    @abstractmethod
    async def sample_parent(self, version=1, **kwargs) -> Optional[Program]:
        pass

    async def visit(self, id, children=1):
        """
        Increments the visit count and calculates advantage for child programs.

        Args:
            id: The ID of the parent program.
            children: The number of new child visits to add. Defaults to 1.
        """
        if children == 0:
            return

        with self.db_client.get_connection() as conn:
            with conn.cursor(cursor_factory=DictCursor) as cur:
                # First update the visit count as before
                cur.execute("SELECT visits FROM programs WHERE id = %s", (id,))
                visits = cur.fetchone()["visits"]
                if visits is None:
                    return

                cur.execute(
                    "UPDATE programs SET visits = visits + %s WHERE id = %s",
                    (children, id),
                )

                # Get all children of this program
                cur.execute(
                    """
                    SELECT id, value 
                    FROM programs 
                    WHERE parent_id = %s AND value IS NOT NULL
                    """,
                    (id,),
                )
                children_data = cur.fetchall()

                if not children_data:
                    return

                # Calculate mean value across all children
                values = [child["value"] for child in children_data]
                mean_value = sum(values) / len(values)

                # Calculate and update advantage for each child
                for child in children_data:
                    advantage = child["value"] - mean_value
                    cur.execute(
                        """
                        UPDATE programs 
                        SET advantage = %s 
                        WHERE id = %s
                        """,
                        (advantage, child["id"]),
                    )
