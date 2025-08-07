import os
from pathlib import Path
import platform
from enum import Enum
from pydantic import BaseModel, Field

ROOT_DIR = Path(__file__).resolve().parent.parent.parent

import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class Scenario(Enum):
    OPEN_WORLD = "open_world"
    DEFAULT_LAB_SCENARIO = "default_lab_scenario"


class Mode(Enum):
    SAVE_BASED = "save-based"
    SCENARIO = "scenario"


def _detect_mods_path(os_name: str) -> str:
    if any(x in os_name for x in ("MINGW", "MSYS", "CYGWIN")):
        path = os.getenv("APPDATA", "")
        mods = Path(path) / "Factorio" / "mods"
        if mods.exists():
            return str(mods)
        return str(
            Path(os.getenv("USERPROFILE", ""))
            / "AppData"
            / "Roaming"
            / "Factorio"
            / "mods"
        )
    return str(
        Path.home()
        / "Applications"
        / "Factorio.app"
        / "Contents"
        / "Resources"
        / "mods"
    )


class DockerConfig(BaseModel):
    """Configuration knobs for Factorio headless servers managed by fle.services.docker."""

    arch: str = Field(default_factory=platform.machine)
    address: str = "localhost"
    os_name: str = Field(default_factory=platform.system)

    saves_path: Path = Field(default_factory=lambda: ROOT_DIR / ".fle" / "saves")
    screenshots_dir: Path = Field(
        default_factory=lambda: ROOT_DIR / "data" / "_screenshots"
    )
    mods_path: str = Field(default_factory=lambda: _detect_mods_path(platform.system()))

    image_name: str = "factoriotools/factorio:1.1.110"
    rcon_port: int = 27015
    udp_port: int = 34197

    scenario_name: str = Scenario.DEFAULT_LAB_SCENARIO.value
    scenario_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.resolve()
        / "factorio"
        / "scenarios"
    )
    server_config_dir: Path = Field(
        default_factory=lambda: Path(__file__).parent.resolve() / "factorio" / "config"
    )

    mode: str = Mode.SAVE_BASED.value
    temp_playing_dir: str = "/opt/factorio/temp/currently-playing"
    name_prefix: str = "factorio_"

    factorio_password: str = Field(
        default_factory=lambda: (
            Path(__file__).parent.resolve() / "factorio" / "config" / "rconpw"
        )
        .read_text()
        .strip()
    )

    model_config = {"extra": "forbid", "frozen": True}
