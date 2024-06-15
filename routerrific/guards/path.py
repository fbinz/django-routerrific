from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest

from routerrific import router

from . import ParameterGuard


@dataclass
class PathGuard(ParameterGuard):
    def __post_init__(self):
        super().__post_init__()
        self.parser = router.build_parser(self.cls)


def from_request(
    guard: PathGuard,
    request: HttpRequest,
    context: router.RouteContext,
) -> Any:
    path_parameters = context.match.groupdict()

    # try to parse the path parameters into the view's parameter types
    try:
        value = path_parameters[guard.name]
        result = guard.parser(value)
        if result is None and guard.parameter.default is not None:
            return guard.parameter.default
        return result
    except Exception as e:
        raise router.MatchFailure("Failed to parse path parameter") from e
