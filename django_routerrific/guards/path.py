from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest

from django_routerrific import router

from . import ParameterGuard


@dataclass
class PathGuard(ParameterGuard):
    def __post_init__(self):
        super().__post_init__()
        self.parser = router.build_serializer(self.cls)


@router.from_request.register
def _(guard: PathGuard, request: HttpRequest, context: router.RouteContext) -> Any:
    path_parameters = context.match.groupdict()

    # try to parse the path parameters into the view's parameter types
    try:
        value = path_parameters[guard.name]
        result = guard.parser(value)
        return result
    except Exception as e:
        raise router.MatchFailure("Failed to parse path parameter") from e
