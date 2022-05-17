from .config import Configuration
from dataclasses import dataclass
from dataclasses import field

import typing


@dataclass
class State:
    configuration: Configuration
    requirements: typing.List[str] = field(default_factory=list)
    constraints: typing.List[str] = field(default_factory=list)
