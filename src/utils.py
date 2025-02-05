from dataclasses import dataclass
from typing import Dict, List, Tuple, Any, Optional
from copy import deepcopy


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
    def from_dict(cls, data: Dict[str, Any]) -> 'ProductionFlows':
        """Create ProductionFlows from a dictionary."""
        crafted = data.get('crafted', [])
        if isinstance(crafted, dict):
            crafted = list(crafted.values())

        return cls(
            input=data.get('input', {}),
            output=data.get('output', {}),
            crafted=crafted,
            harvested=data.get('harvested', {}),
            price_list=data.get('price_list'),
            static_items=data.get('static_items')
        )

    def is_valid(self) -> bool:
        """Check if the production flows data is valid."""
        return isinstance(self.input, dict) and 'output' in self.__dict__


class ProductionAnalyzer:
    """Analyzes production flows and calculates profits/achievements."""

    @staticmethod
    def get_new_flows(pre: ProductionFlows, post: ProductionFlows) -> ProductionFlows:
        """Calculate new production flows between two states."""
        new_flows = ProductionFlows(
            input={},
            output={},
            crafted=[],
            harvested={}
        )

        for flow_key in ['input', 'output', 'harvested']:
            pre_dict = getattr(pre, flow_key)
            post_dict = getattr(post, flow_key)
            new_dict = getattr(new_flows, flow_key)

            for item, value in post_dict.items():
                diff = value - pre_dict.get(item, 0)
                if diff > 0:
                    new_dict[item] = diff

        pre_crafted = deepcopy(pre.crafted)
        for item in post.crafted:
            if item in pre_crafted:
                pre_crafted.remove(item)
            else:
                new_flows.crafted.append(item)

        return new_flows


class ProfitCalculator:
    """Handles profit calculations for production flows."""

    def __init__(self, config: ProfitConfig):
        self.config = config

    def calculate_profits(self, pre: ProductionFlows, post: ProductionFlows) -> Dict[str, float]:
        """Calculate total profits between two production states."""
        if not pre.is_valid() or not post.is_valid():
            return {'static': 0, 'dynamic': 0, 'total': 0}

        new_flows = ProductionAnalyzer.get_new_flows(pre, post)

        static_profits, updated_flows = self._calculate_static_profits(
            new_flows,
            pre.price_list or {},
            self.config.max_static_unit_profit_cap
        )

        dynamic_profits = self._calculate_dynamic_profits(
            updated_flows,
            pre.price_list or {},
            self.config.dynamic_profit_multiplier
        )

        return {
            'static': static_profits,
            'dynamic': dynamic_profits,
            'total': static_profits + dynamic_profits
        }

    def _calculate_static_profits(
            self,
            flows: ProductionFlows,
            price_list: Dict[str, float],
            max_craft_cap: float
    ) -> Tuple[float, ProductionFlows]:
        """Calculate static profits from crafting."""
        static_profits = 0
        updated_flows = deepcopy(flows)

        # Handle harvested items
        self._process_harvested_outputs(updated_flows)

        # Calculate crafting profits
        for craft in updated_flows.crafted:
            profit = self._calculate_craft_profit(
                craft,
                price_list,
                updated_flows,
                max_craft_cap
            )
            static_profits += profit

        return static_profits, updated_flows

    def _process_harvested_outputs(self, flows: ProductionFlows) -> None:
        """Remove harvested items from outputs."""
        for item, value in flows.harvested.items():
            if item in flows.output:
                flows.output[item] -= value
                if flows.output[item] == 0:
                    flows.output.pop(item)

    def _calculate_craft_profit(
            self,
            craft: Dict[str, Any],
            price_list: Dict[str, float],
            flows: ProductionFlows,
            max_craft_cap: float
    ) -> float:
        """Calculate profit for a single crafting operation."""
        count = craft['crafted_count']
        unit_profit = 0

        # Calculate output value
        for item, value in craft['outputs'].items():
            price = price_list.get(item, 0)
            unit_profit += (value / count) * price
            self._update_flow_dict(flows.output, item, value)

        # Subtract input costs
        for item, value in craft['inputs'].items():
            price = price_list.get(item, 0)
            unit_profit -= (value / count) * price
            self._update_flow_dict(flows.input, item, value)

        return unit_profit * (min(max_craft_cap, count) if max_craft_cap > 0 else count)

    def _calculate_dynamic_profits(
            self,
            flows: ProductionFlows,
            price_list: Dict[str, float],
            multiplier: float
    ) -> float:
        """Calculate dynamic profits from production flows."""
        profit = sum(value * price_list.get(item, 0) for item, value in flows.output.items())
        profit -= sum(value * price_list.get(item, 0) for item, value in flows.input.items())
        return profit * multiplier

    @staticmethod
    def _update_flow_dict(flow_dict: Dict[str, float], item: str, value: float) -> None:
        """Update flow dictionary and remove item if value becomes zero."""
        if item in flow_dict:
            flow_dict[item] -= value
            if flow_dict[item] == 0:
                flow_dict.pop(item)


class AchievementTracker:
    """Tracks and calculates achievements from production flows."""

    @staticmethod
    def calculate_achievements(pre: ProductionFlows, post: ProductionFlows) -> Dict[str, Dict[str, float]]:
        """Calculate achievements between two production states."""
        if not pre.is_valid() or not post.is_valid():
            return {'static': {}, 'dynamic': {}}

        post = deepcopy(post)
        post.static_items = AchievementTracker._get_static_items(pre, post)

        return AchievementTracker._process_achievements(pre, post)

    @staticmethod
    def _get_static_items(pre: ProductionFlows, post: ProductionFlows) -> Dict[str, float]:
        """Calculate static items from production flows."""
        new_flows = ProductionAnalyzer.get_new_flows(pre, post)
        static_items = deepcopy(new_flows.harvested)

        for craft in new_flows.crafted:
            for item, value in craft['outputs'].items():
                static_items[item] = static_items.get(item, 0) + value

        return static_items

    @staticmethod
    def _process_achievements(
            pre: ProductionFlows,
            post: ProductionFlows
    ) -> Dict[str, Dict[str, float]]:
        """Process achievements from production flows."""
        achievements = {'static': {}, 'dynamic': {}}

        for item in post.output:
            post_value = post.output[item]
            pre_value = pre.output.get(item, 0)

            if post_value > pre_value:
                created = post_value - pre_value
                static = post.static_items.get(item, 0)

                if static > 0:
                    achievements['static'][item] = static
                if created > static:
                    achievements['dynamic'][item] = created - static

        return achievements


def eval_program_with_profits(
        instance: Any,
        program: str,
        profit_config: Optional[Dict[str, float]] = None
) -> Tuple[List[str], str, bool, Dict[str, float]]:
    """Evaluate a program and calculate profits."""
    config = ProfitConfig(**profit_config) if profit_config else ProfitConfig()
    calculator = ProfitCalculator(config)

    pre_flows = ProductionFlows.from_dict(instance.namespace._get_production_stats())

    try:
        score, goal, result = instance.eval_with_error(program, timeout=300)
        error = False
    except Exception as e:
        result = str(e)
        error = True

    post_flows = ProductionFlows.from_dict(instance.namespace._get_production_stats())
    profits = calculator.calculate_profits(pre_flows, post_flows)

    return result.splitlines(), result, error, profits


def eval_program_with_achievements(
        instance: Any,
        program: str
) -> Tuple[List[str], str, bool, Dict[str, Dict[str, float]]]:
    """Evaluate a program and calculate achievements."""
    pre_flows = ProductionFlows.from_dict(instance.namespace._get_production_stats())

    try:
        score, goal, result = instance.eval_with_error(program, timeout=300)
        error = False
    except Exception as e:
        result = str(e)
        error = True

    post_flows = ProductionFlows.from_dict(instance.namespace._get_production_stats())
    achievements = AchievementTracker.calculate_achievements(pre_flows, post_flows)

    return result.splitlines(), result, error, achievements