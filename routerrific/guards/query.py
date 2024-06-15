from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest

from routerrific import router

from . import ParameterGuard


@dataclass
class QueryGuard(ParameterGuard):
    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        self.parser = router.build_parser(self.cls)


def from_request(
    guard: QueryGuard,
    request: HttpRequest,
    context: router.RouteContext,
) -> Any:
    value = request.GET.get(guard.name)

    try:
        result = guard.parser(value)
        if result is None and guard.parameter.default is not None:
            return guard.parameter.default
        return result
    except Exception as e:
        raise router.MatchFailure(
            f"Failed to parse query parameter {guard.name!r}: {e}"
        ) from e
