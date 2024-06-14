from dataclasses import dataclass
from typing import Any

from django.http import HttpRequest

from django_routerrific import router


@dataclass
class MethodGuard:
    method: str


@router.from_request.register
def _(guard: MethodGuard, request: HttpRequest, context: router.RouteContext) -> Any:
    if request.method.lower() == guard.method.lower():
        return

    raise router.MatchFailure("Method not allowed")
