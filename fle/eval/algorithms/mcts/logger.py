from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.progress import BarColumn, Progress, TaskProgressColumn, TextColumn
from rich.table import Table
from rich.text import Text


@dataclass
class InstanceMetrics:
    """Tracks metrics for a single Factorio instance"""

    instance_id: int
    port: int
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


class FactorioLogger:
    def __init__(self, num_instances: int):
        self.console = Console()
        self.layout = Layout()
        self.instances: Dict[int, InstanceMetrics] = {}
        self.live: Optional[Live] = None
        self.start_time = datetime.now()

        self.progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            expand=True,
        )
        self.progress_task = None

        # Initialize metrics for each instance
        for i in range(num_instances):
            self.instances[i] = InstanceMetrics(instance_id=i, port=34197 + i)

    def start(self):
        """Start the live display with reduced refresh rate and transient=False"""
        self.live = Live(
            self._generate_layout(),
            refresh_per_second=4,  # Reduced from 4
            transient=False,  # Prevents clearing/redrawing
        )
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

    def update_instance(self, instance_id: int, **updates):
        """Update metrics for a specific instance"""
        if instance_id in self.instances:
            instance = self.instances[instance_id]
            for key, value in updates.items():
                if hasattr(instance, key):
                    setattr(instance, key, value)
            instance.last_update = datetime.now()
            if self.live:
                self.live.update(self._generate_layout())

    def _generate_instance_panel(self, instance: InstanceMetrics) -> Panel:
        """Generate a panel for a single instance"""
        table = Table(show_header=False, box=None, padding=(0, 1))
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

        # Add metrics rows
        table.add_row("Program ID:", str(instance.program_id or "None"))
        table.add_row(
            "Status:",
            Text(
                instance.status,
                style="green" if instance.status == "running" else "yellow",
            ),
        )
        table.add_row("Action Reward:", f"{instance.current_reward:.2f}")
        # table.add_row("Holdout Reward:", f"{instance.holdout_value:.2f}")
        table.add_row("Advantage:", f"{instance.relative_reward:.2f}")
        table.add_row(
            "Error Count:",
            Text(
                str(instance.error_count),
                style="red" if instance.error_count > 0 else "white",
            ),
        )
        table.add_row("Total Programs:", str(instance.total_programs))
        table.add_row("Last Update:", instance.last_update.strftime("%H:%M:%S"))
        table.add_row("Avg Time / Program:", Text(avg_time))
        table.add_row(
            "# Entities:",
            Text(
                f"{instance.start_entities} -> {instance.final_entities}",
                style="red"
                if instance.start_entities != instance.final_entities
                else "cyan",
            ),
        )
        table.add_row(
            "# Inventory:",
            Text(
                f"{instance.start_inventory_count} -> {instance.final_inventory_count}"
            ),
        )
        table.add_row(
            "Iteration:", Text(f"{instance.iteration}/{instance.n_iterations}")
        )
        table.add_row("ETA:", Text(eta, style="cyan"))

        return Panel(
            table,
            title=f"Instance {instance.instance_id} (Port: {instance.port})",
            border_style="blue",
        )

    def _generate_layout(self) -> Layout:
        layout = Layout()

        # Create instance metrics layout
        metrics_layout = Layout()
        metrics_layout.split_row(
            *[
                Layout(self._generate_instance_panel(instance), ratio=1)
                for instance in self.instances.values()
            ]
        )

        # Add progress bar if it exists
        if self.progress_task is not None:
            layout.split_column(
                Layout(metrics_layout, ratio=4), Layout(self.progress, ratio=1)
            )
        else:
            layout = metrics_layout

        return layout
