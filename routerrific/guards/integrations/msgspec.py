from typing import Any

import msgspec
from django.http import HttpRequest

from routerrific import router
from routerrific.guards.parameter import ParameterGuard


def from_request(
    guard: ParameterGuard[msgspec.Struct],
    request: HttpRequest,
    context: router.RouteContext,
) -> Any:
    try:
        result = msgspec.json.decode(request.body, type=guard.parameter.annotation)
        return result
    except (msgspec.ValidationError, msgspec.DecodeError) as e:
        raise router.MatchFailure(f"Invalid body: {e}") from e
