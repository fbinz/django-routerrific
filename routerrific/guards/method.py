from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest

from routerrific import router


@dataclass
class MethodGuard:
    method: str


def from_request(
    guard: MethodGuard,
    request: HttpRequest,
    context: router.RouteContext,
) -> Any:
    if request.method.lower() == guard.method.lower():
        return

    raise router.MatchFailure("Method not allowed")
