from typing import Dict, Any, List, Optional
from dataclasses import dataclass
import numpy as np
import json
from fle.commons.models.technology_state import TechnologyState
from fle.commons.models.research_state import ResearchState
from fle.commons.models.achievements import ProductionFlows
from fle.agents import TaskResponse
from fle.env.entities import Inventory


@dataclass
class GameInfo:
    """Represents game timing and speed information"""

    tick: int
    time: float
    speed: float


@dataclass
class AgentMessage:
    """Represents a message from another agent"""

    sender: str
    content: str
    timestamp: float


@dataclass
class TaskInfo:
    """Represents task information and objectives"""

    goal_description: str
    agent_instructions: Optional[str]
    task_key: str
    trajectory_length: int


@dataclass
class CharacterPosition:
    """Represents a character/player position"""

    agent_idx: int
    x: float
    y: float


@dataclass
class Observation:
    """Complete observation of the game state"""

    raw_text: str
    entities: List[Dict[str, Any]]  # Entity dicts from Pydantic __dict__
    inventory: Inventory
    research: ResearchState
    game_info: GameInfo
    score: float
    automated_score: float  # Score excluding harvested and manually crafted items
    flows: ProductionFlows
    task_verification: Optional[TaskResponse]
    messages: List[AgentMessage]
    serialized_functions: List[Dict[str, Any]]
    task_info: Optional[TaskInfo]
    map_image: str  # Base64 encoded PNG image
    character_positions: List[CharacterPosition]  # Position of each character/agent

    @classmethod
    def from_dict(cls, obs_dict: Dict[str, Any]) -> "Observation":
        """Create an Observation from a dictionary matching the gym observation space"""
        # Entities are already strings, no need to parse
        entities = obs_dict.get("entities", [])

        # Convert inventory
        inventory = Inventory()
        for item in obs_dict.get("inventory", []):
            inventory[item["type"]] = item["quantity"]

        # Convert research state
        research = ResearchState(
            technologies={
                tech["name"]: TechnologyState(
                    name=tech["name"],
                    researched=bool(tech["researched"]),
                    enabled=bool(tech["enabled"]),
                    level=tech["level"],
                    research_unit_count=tech["research_unit_count"],
                    research_unit_energy=tech["research_unit_energy"],
                    prerequisites=tech["prerequisites"],
                    ingredients={
                        item["item"]: item["amount"] for item in tech["ingredients"]
                    },
                )
                for tech in obs_dict.get("research", {}).get("technologies", [])
            },
            current_research=obs_dict.get("research", {}).get("current_research"),
            research_progress=obs_dict.get("research", {}).get(
                "research_progress", 0.0
            ),
            research_queue=obs_dict.get("research", {}).get("research_queue", []),
            progress={
                item["name"]: item["value"]
                for item in obs_dict.get("research", {}).get("progress", [])
            },
        )

        # Convert game info
        game_info = GameInfo(
            tick=obs_dict.get("game_info", {}).get("tick", 0),
            time=obs_dict.get("game_info", {}).get("time", 0.0),
            speed=obs_dict.get("game_info", {}).get("speed", 0.0),
        )

        # Convert flows
        flows_dict = obs_dict.get("flows", {})
        # Transform from observation space format back to ProductionFlows format
        transformed_flows = {
            "input": {
                item["type"]: item["rate"] for item in flows_dict.get("input", [])
            },
            "output": {
                item["type"]: item["rate"] for item in flows_dict.get("output", [])
            },
            "crafted": flows_dict.get("crafted", []),  # Already in correct format
            "harvested": {
                item["type"]: item["amount"] for item in flows_dict.get("harvested", [])
            },
            "price_list": {
                item["type"]: item["price"] for item in flows_dict.get("price_list", [])
            }
            if flows_dict.get("price_list")
            else None,
            "static_items": {
                item["type"]: item["value"]
                for item in flows_dict.get("static_items", [])
            }
            if flows_dict.get("static_items")
            else None,
        }
        flows = ProductionFlows.from_dict(transformed_flows)

        # Convert task verification if present
        task_verification = None
        if obs_dict.get("task_verification"):
            task_verification = TaskResponse(
                success=bool(obs_dict["task_verification"]["success"]),
                meta={
                    item["key"]: json.loads(item["value"])
                    for item in obs_dict["task_verification"].get("meta", [])
                },
            )

        # Convert messages
        messages = [
            AgentMessage(
                sender=msg["sender"], content=msg["content"], timestamp=msg["timestamp"]
            )
            for msg in obs_dict.get("messages", [])
        ]

        # Get serialized functions
        serialized_functions = obs_dict.get("serialized_functions", [])

        # Convert task info - task_info dict should always be present now
        task_info = None
        task_dict = obs_dict.get("task_info", {})
        # Only create TaskInfo if there's actual task data (non-empty goal_description indicates real task)
        if task_dict.get("goal_description"):
            # Convert empty string back to None for agent_instructions to maintain consistency
            agent_instructions = task_dict.get("agent_instructions")
            if agent_instructions == "":
                agent_instructions = None

            task_info = TaskInfo(
                goal_description=task_dict.get("goal_description", ""),
                agent_instructions=agent_instructions,
                task_key=task_dict.get("task_key", ""),
                trajectory_length=task_dict.get("trajectory_length", 0),
            )

        # Get map image (base64 encoded string)
        map_image = obs_dict.get("map_image", "")

        # Convert character positions
        character_positions = [
            CharacterPosition(
                agent_idx=pos["agent_idx"],
                x=pos["x"],
                y=pos["y"],
            )
            for pos in obs_dict.get("character_positions", [])
        ]

        return cls(
            raw_text=obs_dict.get("raw_text", ""),
            entities=entities,  # Now just passing the list of strings
            inventory=inventory,
            research=research,
            game_info=game_info,
            score=obs_dict.get("score", 0.0),
            automated_score=obs_dict.get("automated_score", 0.0),
            flows=flows,
            task_verification=task_verification,
            messages=messages,
            serialized_functions=serialized_functions,
            task_info=task_info,
            map_image=map_image,
            character_positions=character_positions,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Observation to a dictionary matching the gym observation space"""
        flows_dict = self.flows.to_dict()

        # Transform flows to match observation space structure
        transformed_flows = {
            "input": [{"type": k, "rate": v} for k, v in flows_dict["input"].items()],
            "output": [{"type": k, "rate": v} for k, v in flows_dict["output"].items()],
            "crafted": flows_dict["crafted"],  # Already in correct format
            "harvested": [
                {"type": k, "amount": v} for k, v in flows_dict["harvested"].items()
            ],
            "price_list": [
                {"type": k, "price": v}
                for k, v in (flows_dict["price_list"] or {}).items()
            ],
            "static_items": [
                {"type": k, "value": v}
                for k, v in (flows_dict["static_items"] or {}).items()
            ],
        }

        return {
            "raw_text": self.raw_text,
            "map_image": self.map_image,
            "entities": self.entities,  # Use string representation of entities
            "inventory": [
                {"quantity": np.int32(v), "type": k}
                for k, v in self.inventory.items()
                if v > 0
            ],
            "research": {
                "technologies": [
                    {
                        "name": tech.name,
                        "researched": int(tech.researched),
                        "enabled": int(tech.enabled),
                        "level": tech.level,
                        "research_unit_count": tech.research_unit_count,
                        "research_unit_energy": tech.research_unit_energy,
                        "prerequisites": tech.prerequisites,
                        "ingredients": [],
                    }
                    for tech in self.research.technologies.values()
                ],
                "current_research": self.research.current_research
                if self.research.current_research is not None
                else "None",
                "research_progress": self.research.research_progress,
                "research_queue": self.research.research_queue,
                "progress": [
                    {"name": name, "value": value}
                    for name, value in self.research.progress.items()
                ]
                if self.research.progress
                else "None",
            },
            "game_info": {
                "tick": self.game_info.tick,
                "time": self.game_info.time,
                "speed": self.game_info.speed,
            },
            "score": self.score,
            "automated_score": self.automated_score,
            "flows": transformed_flows,
            "task_verification": {
                "success": int(self.task_verification.success),
                "meta": [
                    {"key": k, "value": json.dumps(v)}
                    for k, v in self.task_verification.meta.items()
                ],
            }
            if self.task_verification
            else {"success": 0, "meta": []},
            "messages": [
                {
                    "sender": msg.sender,
                    "content": msg.content,
                    "timestamp": msg.timestamp,
                }
                for msg in self.messages
            ],
            "serialized_functions": self.serialized_functions,
            "task_info": {
                "goal_description": self.task_info.goal_description
                if self.task_info
                else "",
                "agent_instructions": (self.task_info.agent_instructions or "")
                if self.task_info
                else "",  # Convert None to empty string for gym space
                "task_key": self.task_info.task_key if self.task_info else "",
                "trajectory_length": self.task_info.trajectory_length
                if self.task_info
                else 0,
            },  # Always provide a task_info dict, even if empty
            "character_positions": [
                {
                    "agent_idx": pos.agent_idx,
                    "x": pos.x,
                    "y": pos.y,
                }
                for pos in self.character_positions
            ],
        }
