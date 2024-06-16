import inspect
from dataclasses import dataclass
from typing import Generic, Type, TypeVar

T = TypeVar("T")


@dataclass
class ParameterGuard(Generic[T]):
    parameter: inspect.Parameter
    cls: Type[T]

    def __post_init__(self):
        self.name = self.parameter.name
