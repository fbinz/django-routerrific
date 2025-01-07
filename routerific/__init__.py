"""Terrific routing for Django."""

__version__ = "0.1.1"

from typing import TypeAlias

from routerific.guards import (
    HeaderGuard,
    MethodGuard,
    PathGuard,
    QueryGuard,
)

from .router import Router, route
