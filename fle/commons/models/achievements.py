from copy import deepcopy
from dataclasses import dataclass
from typing import Dict, List, Any, Optional


@dataclass
class ProfitConfig:
    """Configuration for profit calculations."""

    max_static_unit_profit_cap: float = 5.0
    dynamic_profit_multiplier: float = 10.0


@dataclass
class ProductionFlows:
    """Represents production flow data."""

    input: Dict[str, float]
    output: Dict[str, float]
    crafted: List[Dict[str, Any]]
    harvested: Dict[str, float]
    price_list: Optional[Dict[str, float]] = None
    static_items: Optional[Dict[str, float]] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ProductionFlows":
        """Create ProductionFlows from a dictionary."""
        crafted = data.get("crafted", [])
        if isinstance(crafted, dict):
            crafted = list(crafted.values())

        return cls(
            input=data.get("input", {}),
            output=data.get("output", {}),
            crafted=crafted,
            harvested=data.get("harvested", {}),
            price_list=data.get("price_list"),
            static_items=data.get("static_items"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ProductionFlows to a dictionary."""
        return {
            "input": self.input,
            "output": self.output,
            "crafted": self.crafted,
            "harvested": self.harvested,
            "price_list": self.price_list,
            "static_items": self.static_items,
        }

    def is_valid(self) -> bool:
        """Check if the production flows data is valid."""
        return isinstance(self.input, dict) and "output" in self.__dict__

    def get_new_flows(
        cls: "ProductionFlows", post: "ProductionFlows"
    ) -> "ProductionFlows":
        """Calculate new production flows between two states."""
        new_flows = ProductionFlows(input={}, output={}, crafted=[], harvested={})

        for flow_key in ["input", "output", "harvested"]:
            pre_dict = getattr(cls, flow_key)
            post_dict = getattr(post, flow_key)
            new_dict = getattr(new_flows, flow_key)

            for item, value in post_dict.items():
                diff = value - pre_dict.get(item, 0)
                if diff > 0:
                    new_dict[item] = diff

        pre_crafted = deepcopy(cls.crafted)
        for item in post.crafted:
            if item in pre_crafted:
                pre_crafted.remove(item)
            else:
                new_flows.crafted.append(item)

        return new_flows
