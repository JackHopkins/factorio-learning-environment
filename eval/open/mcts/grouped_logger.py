from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.text import Text
from rich.box import SIMPLE


@dataclass
class InstanceGroupMetrics:
    """Tracks metrics for a group of instances running parallel MCTS"""

    group_id: int
    instances: Dict[int, "InstanceMetrics"]


@dataclass
class InstanceMetrics:
    """Tracks metrics for a single Factorio instance"""

    tcp_port: int
    is_holdout: bool = False
    program_id: Optional[int] = None
    current_reward: float = 0.0
    raw_reward: float = 0.0
    holdout_value: float = 0.0
    relative_reward: float = 0.0
    status: str = "idle"
    last_update: datetime = field(default_factory=datetime.now)
    error_count: int = 0
    total_programs: int = 0
    start_entities: int = 0
    final_entities: int = 0
    start_inventory_count: int = 0
    final_inventory_count: int = 0
    version: int = 0
    version_description: str = "N/A"
    iteration: int = 0
    n_iterations: int = 0


class GroupedFactorioLogger:
    """Logger that displays instances grouped by their MCTS parallel groups"""

    def __init__(
        self, n_groups: int, instances_per_group: int, base_port=27000, resume_version=0
    ):
        self.console = Console()
        self.layout = Layout()
        self.groups: Dict[int, InstanceGroupMetrics] = {}
        self.live: Optional[Live] = None
        self.start_time = datetime.now()
        self.n_groups = n_groups
        self.instances_per_group = instances_per_group
        self.port_to_group: Dict[int, int] = {}  # Maps tcp_port to group_id
        self.resume_version = resume_version

        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            expand=True,
        )
        self.progress_task = None

        # Initialize metrics for each group and their instances
        current_port = base_port

        for group_id in range(n_groups):
            group_instances = {}
            for i in range(instances_per_group):
                # is_holdout = (i == instances_per_group - 1)  # Last instance in group is holdout
                group_instances[current_port] = InstanceMetrics(
                    tcp_port=current_port, is_holdout=False
                )
                self.port_to_group[current_port] = group_id
                current_port += 1

            self.groups[group_id] = InstanceGroupMetrics(
                group_id=group_id, instances=group_instances
            )

    def start(self):
        """Start the live display"""
        self.live = Live(self._generate_layout(), refresh_per_second=4, transient=False)
        self.live.start()

    def stop(self):
        """Stop the live display"""
        if self.live:
            self.live.stop()

    def update_progress(self, advance: int = 1):
        if self.progress_task is not None:
            self.progress.update(self.progress_task, advance=advance)
            if self.live:
                self.live.update(self._generate_layout())

    def update_instance(self, tcp_port: int, **updates):
        """Update metrics for a specific instance using its tcp_port"""
        group_id = self.port_to_group.get(tcp_port)
        if group_id is not None and group_id in self.groups:
            group = self.groups[group_id]
            if tcp_port in group.instances:
                instance = group.instances[tcp_port]
                for key, value in updates.items():
                    if hasattr(instance, key):
                        setattr(instance, key, value)
                instance.last_update = datetime.now()
                if self.live:
                    self.live.update(self._generate_layout())

    def _generate_instance_panel(
        self, instance: InstanceMetrics, group_id: int
    ) -> Panel:
        """Generate a panel for a single instance with two-column layout"""
        # Create two tables for left and right columns
        left_table = Table(show_header=False, box=None, padding=(0, 1))
        right_table = Table(show_header=False, box=None, padding=(0, 1))

        # Calculate average time
        avg_time = "N/A"
        if instance.total_programs > 0:
            avg_time = f"{((datetime.now() - self.start_time).total_seconds() / instance.total_programs):.2f} sec"

        # Calculate ETA
        eta = "N/A"
        if instance.iteration > 0:
            elapsed_time = (datetime.now() - self.start_time).total_seconds()
            time_per_iteration = elapsed_time / instance.iteration
            remaining_iterations = instance.n_iterations - instance.iteration
            estimated_remaining_seconds = time_per_iteration * remaining_iterations
            eta_time = datetime.now() + timedelta(seconds=estimated_remaining_seconds)
            eta = eta_time.strftime("%H:%M:%S")

        # Left column data
        left_table.add_row("Program ID:", str(instance.program_id or "None"))
        left_table.add_row(
            "Status:",
            Text(
                instance.status,
                style="green" if instance.status == "running" else "yellow",
            ),
        )
        left_table.add_row("Reward:", f"{instance.current_reward:.2f}")
        # left_table.add_row("Holdout:", f"{instance.holdout_value:.2f}")
        left_table.add_row("Advantage:", f"{instance.relative_reward:.2f}")
        left_table.add_row(
            "Error Count:",
            Text(
                str(instance.error_count),
                style="red" if instance.error_count > 0 else "white",
            ),
        )
        left_table.add_row("ETA:", Text(eta, style="cyan"))

        # Right column data
        right_table.add_row("Total Programs:", str(instance.total_programs))
        right_table.add_row("Last Update:", instance.last_update.strftime("%H:%M:%S"))
        right_table.add_row("Avg Time/Prog:", Text(avg_time))
        right_table.add_row(
            "Entities:",
            Text(
                f"{instance.start_entities} → {instance.final_entities}",
                style="red"
                if instance.start_entities != instance.final_entities
                else "cyan",
            ),
        )
        right_table.add_row(
            "Inventory:",
            Text(
                f"{instance.start_inventory_count} → {instance.final_inventory_count}"
            ),
        )
        right_table.add_row("Version:", Text(f"v{instance.version}"))
        right_table.add_row(
            "Iteration:", Text(f"{instance.iteration}/{instance.n_iterations}")
        )
        # Create a container table to hold both columns
        container = Table.grid(padding=(0, 2))
        container.add_row(left_table, right_table)

        title = f"Instance (Port: {instance.tcp_port})"

        return Panel(container, title=title, border_style="blue", padding=(0, 1))

    def _generate_group_layout(self, group: InstanceGroupMetrics) -> Panel:
        """Generate layout for a single group of instances"""
        group_layout = Layout()

        # Create panels for active instances and holdout
        active_instances = [
            inst for inst in group.instances.values() if not inst.is_holdout
        ]
        # holdout_instance = next(inst for inst in group.instances.values() if inst.is_holdout)

        # Create the instance panels
        instance_panels = [
            self._generate_instance_panel(inst, group.group_id)
            for inst in active_instances
        ]
        # instance_panels.append(self._generate_instance_panel(holdout_instance, group.group_id))

        # Split the layout horizontally for all instances in the group
        group_layout.split_row(*[Layout(panel, ratio=1) for panel in instance_panels])

        # Use a more compact panel style with reduced padding and simplified border
        return Panel(
            group_layout,
            # title=f"Group {group.group_id}",  # Shortened title
            border_style="green",
            padding=(0, 0),  # Reduce vertical and horizontal padding
            box=SIMPLE,  # Use simpler border style
        )

    def _generate_layout(self) -> Layout:
        """Generate the complete layout with all groups"""
        main_layout = Layout()

        # Create layouts for each group
        group_layouts = [
            self._generate_group_layout(group) for group in self.groups.values()
        ]

        # Split vertically for each group
        main_layout.split_column(
            *[Layout(layout, ratio=1, minimum_size=3) for layout in group_layouts]
        )

        # Add progress bar if it exists
        if self.progress_task is not None:
            final_layout = Layout()
            final_layout.split_column(
                Layout(main_layout, ratio=4), Layout(self.progress, ratio=1)
            )
            return final_layout

        return main_layout
