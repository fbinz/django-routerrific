import importlib
import inspect
import re
import typing
from dataclasses import dataclass
from functools import reduce, singledispatch, wraps
from typing import Any, Callable
from uuid import UUID

import msgspec
from django.http import HttpRequest, HttpResponseNotFound
from more_itertools import collapse

import django_routerrific.guards as guards

from .expr import Expr

GUARDS_ATTR = "_guards"


class MatchFailure(Exception):
    pass


class RouteConfigurationException(Exception):
    pass


DESERIALIZERS = {
    int: int,
    str: str,
    UUID: UUID,
}

DJANGO_PATTERNS = {
    "int": r"\d+",
    "str": r"[^/]+",
    "slug": r"[a-zA-Z0-9-_]+",
    "uuid": r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    "path": r".+",
}


def path_to_pattern(path: str) -> re.Pattern:
    def replacer(match):
        name = match.group("name")
        type_ = match.group("type")
        pattern = DJANGO_PATTERNS[type_]
        return f"(?P<{name}>{pattern})"

    # This regex tries to match django-style path parameters, but
    # not regex-style named capture groups. This seems somewhat brittle,
    # but we'll go with it for now.
    param_regex = re.compile(r"(?<!\?P)<((?P<type>[^:]+):)?(?P<name>[^>]+)>")
    regexed_pattern = param_regex.sub(replacer, path)
    return re.compile(regexed_pattern)


def path_parameter_names(path: str) -> list[str]:
    pattern = path_to_pattern(path)
    return list(pattern.groupindex.keys())


def build_serializer(cls: type) -> Callable[[str], Any]:
    predicate = None

    if typing.get_origin(cls) is typing.Annotated:
        args = typing.get_args(cls)
        cls = args[0]

        exprs = [expr for expr in args[1:] if isinstance(expr, Expr)]
        if exprs:
            expr = reduce(lambda a, b: a & b, exprs)
            predicate = expr.compile()
    else:
        cls = cls

    try:
        deserializer = DESERIALIZERS[cls]
    except KeyError:
        raise RouteConfigurationException(f"Unsupported type {cls.__name__!r}")

    def parse(value):
        deserialized_value = deserializer(value)
        if predicate is None:
            return deserialized_value

        if not predicate(deserialized_value):
            raise ValueError

        return deserialized_value

    return parse


@dataclass
class RouteContext:
    match: re.Match


@singledispatch
def from_request(obj, request: HttpRequest, context: RouteContext) -> Any:
    raise NotImplementedError


@dataclass
class RouterMatch:
    view: Callable[..., Any]
    args: dict[str, Any]


@dataclass
class Router:
    def __init__(self, views: list[Callable[..., Any]] | None = None):
        if views is None:
            views = []
            
        self.views = list(collapse(views))

    @staticmethod
    def _from_request(guard, request, context):
        if not isinstance(guard, guards.ParameterGuard):
            return from_request(guard, request, context)

        cls = guard.parameter.annotation
        is_guard = isinstance(guard, guards.ParameterGuard)
        is_type = isinstance(cls, type)

        if is_guard and is_type and cls in from_request.registry:
            return from_request.registry[cls](cls, request, context)

        return from_request(guard, request, context)

    def match(self, request) -> RouterMatch | None:
        candidates = []

        for view in self.views:
            view_gards: list[ViewGuard] = getattr(view, GUARDS_ATTR, [])
            for view_guard in view_gards:

                match = view_guard.path_pattern.fullmatch(request.path)
                if match is None:
                    continue

                context = RouteContext(match=match)
                try:
                    args = {}
                    for guard in view_guard.guards:
                        value = self._from_request(guard, request, context)
                        if isinstance(guard, guards.ParameterGuard):
                            args[guard.name] = value

                    candidates.append(RouterMatch(view, args))
                except MatchFailure:
                    continue

        return next(iter(candidates), None)

    def dispatch(self, request):
        match = self.match(request)
        if match is None:
            return HttpResponseNotFound()

        return match.view(**match.args)


def include(path: str):
    module, member = path.rsplit(".", 1)
    module = importlib.import_module(module)
    views = getattr(module, member)
    assert isinstance(views, list)
    return views


def cls_or_str(cls: type) -> type:
    if cls is inspect.Parameter.empty:
        return str
    return cls


def implicitly_located_guard(
    path: str, parameter: inspect.Parameter
) -> guards.ParameterGuard:
    cls = cls_or_str(parameter.annotation)
    if parameter.name in path_parameter_names(path):
        return guards.PathGuard(parameter=parameter, cls=cls)

    if isinstance(cls, type):
        if issubclass(cls, msgspec.Struct):
            return guards.BodyGuard(parameter=parameter, cls=cls)

        if from_request.registry.get(cls) is not None:
            return guards.ParameterGuard(parameter=parameter, cls=cls)

    return guards.QueryGuard(parameter=parameter, cls=cls)


def explicitly_located_guard(parameter: inspect.Parameter) -> guards.ParameterGuard:
    args = typing.get_args(parameter.annotation)
    cls = parameter.annotation
    for arg in args:
        if is_explicit_guard(arg):
            return arg(parameter=parameter, cls=cls)

    return None


def is_explicit_guard(cls) -> bool:
    for guard in (
        guards.HeaderGuard,
        guards.QueryGuard,
        guards.PathGuard,
        guards.BodyGuard,
    ):
        if cls is guard:
            return True

    return False


def parameter_guard(
    *, parameter: inspect.Parameter, path: str
) -> guards.ParameterGuard:
    if guard := explicitly_located_guard(parameter=parameter):
        return guard

    return implicitly_located_guard(parameter=parameter, path=path)


def view_guards(
    view: Callable[..., Any], method: str, path: str
) -> list[guards.ParameterGuard]:
    signature = inspect.signature(view)

    return [
        guards.MethodGuard(method=method),
        *(
            parameter_guard(path=path, parameter=parameter)
            for parameter in signature.parameters.values()
        ),
    ]


@dataclass
class ViewGuard:
    guards: list[guards.ParameterGuard]
    path_pattern: re.Pattern


def route(method, path: str):
    def decorator(view):
        path_pattern = path_to_pattern(path)
        view_guard = ViewGuard(
            guards=view_guards(view, method, path), path_pattern=path_pattern
        )

        # check if all path parameters are actually instantiated as path guards
        for name in path_pattern.groupindex.keys():
            for guard in view_guard.guards:
                if isinstance(guard, guards.PathGuard) and guard.name == name:
                    break
            else:
                raise RouteConfigurationException(
                    f"Path parameter named {name!r} not found in view function"
                )

        if getattr(view, GUARDS_ATTR, None) is None:
            setattr(view, GUARDS_ATTR, [view_guard])
        else:
            getattr(view, GUARDS_ATTR).append(view_guard)

        @wraps(view)
        def wrapper(*args, **kwargs):
            return view(*args, **kwargs)

        return wrapper

    return decorator
