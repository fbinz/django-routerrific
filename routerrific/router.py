import importlib
import inspect
import re
import typing
from dataclasses import dataclass
from functools import reduce
from types import NoneType
from typing import Any, Callable, Iterable
from uuid import UUID

from django.http import HttpResponseNotFound
from more_itertools import collapse

import routerrific.guards as guards
from routerrific.guards.parameter import ParameterGuard

from .expr import Expr

GUARDS_ATTR = "_guards"


class MatchFailure(Exception):
    pass


class RouteConfigurationException(Exception):
    pass


def parse_str(value):
    if value is None:
        raise ValueError
    return str(value)


DESERIALIZERS = {
    int: int,
    str: parse_str,
    UUID: UUID,
    NoneType: lambda _: None,
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


def build_parser(cls: type) -> Callable[[str], Any]:
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
        if args := typing.get_args(cls):
            deserializers = [DESERIALIZERS[arg] for arg in args]
        else:
            deserializers = [DESERIALIZERS[cls]]
    except KeyError:
        raise RouteConfigurationException(f"Unsupported type {cls.__name__!r}")

    def parse(value):
        for deserializer in deserializers:
            try:
                deserialized_value = deserializer(value)
                if predicate is None:
                    return deserialized_value

                if not predicate(deserialized_value):
                    continue

                return deserialized_value
            except Exception:
                continue

        raise ValueError

    return parse


@dataclass
class RouteContext:
    match: re.Match


@dataclass
class RouterMatch:
    view: Callable[..., Any]
    args: dict[str, Any]


@dataclass
class ViewGuard:
    view: Callable[..., Any]
    guards: list[guards.ParameterGuard]
    path_pattern: re.Pattern


@dataclass
class Router:
    def __init__(
        self,
        views: list[Callable[..., Any]] | None = None,
        integrations: list[str | Callable[..., Any]] | None = None,
    ):
        self.guard_registry = {}

        # register standard types
        from routerrific.guards import header, method, path, query

        self.register_guard(header.from_request)
        self.register_guard(method.from_request)
        self.register_guard(path.from_request)
        self.register_guard(query.from_request)

        if integrations is not None:
            for integration in integrations:
                self.register_guard(integration)

        self.view_guards = list(collapse(map(self.view_guard, views or [])))

    def register_guard(self, fn: str | Callable[..., Any]) -> None:
        if isinstance(fn, str):
            fn_split = fn.rsplit(".", 1)
            if len(fn_split) == 1:
                module_name = f"routerrific.guards.integrations.{fn}"
                attr_name = "from_request"
            else:
                module_name, attr_name = fn_split

            module = importlib.import_module(module_name)
            fn = getattr(module, attr_name)

        signature = inspect.signature(fn)
        cls = next(iter(signature.parameters.values())).annotation

        if typing.get_origin(cls) == ParameterGuard and (args := typing.get_args(cls)):
            cls = args[0]

        self.guard_registry[cls] = fn

    def view_guard(self, view: Callable[..., Any]) -> Iterable[ViewGuard]:
        routerrific = getattr(view, "__routerrific__", None)
        if routerrific is None:
            raise RouteConfigurationException(
                "View function must be annotated with @route"
            )

        for method, path in routerrific:
            path_pattern = path_to_pattern(path)
            view_guard = ViewGuard(
                guards=self.view_guards(view, method, path),
                path_pattern=path_pattern,
                view=view,
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

            yield view_guard

    def _from_request(self, guard, request, context):
        if not isinstance(guard, guards.ParameterGuard):
            fn = self.guard_registry[guard.__class__]
            return fn(guard, request, context)

        cls = guard.parameter.annotation
        is_guard = isinstance(guard, guards.ParameterGuard)
        is_type = isinstance(cls, type)

        if is_guard and is_type and (fn := self.guard_registry.get(guard.cls)):
            return fn(guard, request, context)

        fn = self.guard_registry[guard.__class__]
        return fn(guard, request, context)

    def match(self, request) -> RouterMatch | None:
        candidates = []

        for view_guard in self.view_guards:
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

                candidates.append(RouterMatch(view_guard.view, args))
            except MatchFailure:
                continue

        return next(iter(candidates), None)

    def dispatch(self, request):
        match = self.match(request)
        if match is None:
            return HttpResponseNotFound()

        return match.view(**match.args)

    @staticmethod
    def include(path: str):
        module, member = path.rsplit(".", 1)
        module = importlib.import_module(module)
        views = getattr(module, member)
        assert isinstance(views, list)
        return views

    @staticmethod
    def cls_or_str(cls: type) -> type:
        if cls is inspect.Parameter.empty:
            return str
        return cls

    def implicitly_located_guard(
        self, path: str, parameter: inspect.Parameter
    ) -> guards.ParameterGuard:
        cls = Router.cls_or_str(parameter.annotation)
        if parameter.name in path_parameter_names(path):
            return guards.PathGuard(parameter=parameter, cls=cls)

        if isinstance(cls, type):
            if self.guard_registry.get(cls) is not None:
                return guards.ParameterGuard(parameter=parameter, cls=cls)

            if self.guard_registry.get(cls.__bases__[0]) is not None:
                cls = cls.__bases__[0]
                return guards.ParameterGuard(parameter=parameter, cls=cls)

        return guards.QueryGuard(parameter=parameter, cls=cls)

    def explicitly_located_guard(
        self, parameter: inspect.Parameter
    ) -> guards.ParameterGuard:
        args = typing.get_args(parameter.annotation)
        cls = parameter.annotation
        for arg in args:
            if self.is_explicit_guard(arg):
                return arg(parameter=parameter, cls=cls)

        return None

    @staticmethod
    def is_explicit_guard(cls) -> bool:
        for guard in (
            guards.HeaderGuard,
            guards.QueryGuard,
            guards.PathGuard,
        ):
            if cls is guard:
                return True

        return False

    def parameter_guard(
        self, *, parameter: inspect.Parameter, path: str
    ) -> guards.ParameterGuard:
        if guard := self.explicitly_located_guard(parameter=parameter):
            return guard

        return self.implicitly_located_guard(parameter=parameter, path=path)

    def view_guards(
        self, view: Callable[..., Any], method: str, path: str
    ) -> list[guards.ParameterGuard]:
        signature = inspect.signature(view)

        return [
            guards.MethodGuard(method=method),
            *(
                self.parameter_guard(path=path, parameter=parameter)
                for parameter in signature.parameters.values()
            ),
        ]


def route(method, path: str):
    def decorator(view):
        if not hasattr(view, "__routerrific__"):
            setattr(view, "__routerrific__", [(method, path)])
        else:
            getattr(view, "__routerrific__").append((method, path))

        return view

    return decorator
