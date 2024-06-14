from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest

from django_routerrific import router

from . import ParameterGuard


@dataclass
class QueryGuard(ParameterGuard):
    def __post_init__(self, *args, **kwargs):
        super().__post_init__(*args, **kwargs)
        self.parser = router.build_serializer(self.cls)


@router.from_request.register
def _(guard: QueryGuard, request: HttpRequest, context: router.RouteContext) -> Any:
    value = request.GET.get(guard.name)
    if value is None:
        raise router.MatchFailure(f"Query parameter {guard.name!r} not found")

    try:
        result = guard.parser(value)
        return result
    except Exception as e:
        raise router.MatchFailure(
            f"Failed to parse query parameter {guard.name!r}: {e}"
        ) from e
