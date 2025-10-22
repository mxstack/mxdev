from .config import Configuration
from dataclasses import dataclass
from dataclasses import field

import typing


@dataclass
class State:
    configuration: Configuration
    requirements: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
