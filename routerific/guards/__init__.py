from typing import TypeAlias

from routerific.guards.parameter import ParameterGuard

from .header import HeaderGuard
from .method import MethodGuard
from .path import PathGuard
from .query import QueryGuard

Query: TypeAlias = QueryGuard
Method: TypeAlias = MethodGuard
Path: TypeAlias = PathGuard
Header: TypeAlias = HeaderGuard
