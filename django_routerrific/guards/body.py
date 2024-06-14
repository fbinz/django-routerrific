from dataclasses import dataclass
from typing import Any

import msgspec
from django.http import HttpRequest

from django_routerrific import router

from . import ParameterGuard


@dataclass
class BodyGuard(ParameterGuard):
    """Pun not intended."""


@router.from_request.register
def _(guard: BodyGuard, request: HttpRequest, context: router.RouteContext) -> Any:
    assert issubclass(guard.cls, msgspec.Struct)
    try:
        result = msgspec.json.decode(request.body, type=guard.cls)
        return result
    except msgspec.ValidationError as e:
        raise router.MatchFailure(f"Invalid body: {e}") from e
