import inspect
from dataclasses import dataclass


@dataclass
class ParameterGuard:
    parameter: inspect.Parameter
    cls: type

    def __post_init__(self):
        self.name = self.parameter.name
