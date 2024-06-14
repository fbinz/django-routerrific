from typing import TypeAlias

from django_routerrific.guards.parameter import ParameterGuard

from .body import BodyGuard
from .header import HeaderGuard
from .method import MethodGuard
from .path import PathGuard
from .query import QueryGuard

Query: TypeAlias = QueryGuard
Body: TypeAlias = BodyGuard
Method: TypeAlias = MethodGuard
Path: TypeAlias = PathGuard
Header: TypeAlias = HeaderGuard
