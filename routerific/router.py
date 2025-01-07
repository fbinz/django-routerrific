from collections import defaultdict
from typing import Any, Callable

from dataclasses import dataclass, field
from django.urls import path


@dataclass
class Router:
    context_factory: Callable[..., dict[str, Any]]

    registry: Any = field(default_factory=lambda: defaultdict(list))
    paths: list[Any] = field(default_factory=list)

    @property
    def urls(self):
        return self.paths

    def guard(self, *paths, handler=None, **kwargs):
        if not handler:

            def decorator(decoratee):
                for p in paths:
                    self.registry[p.name].append((kwargs, decoratee))
                    self.paths.append(p)

                return decoratee

            return decorator
        else:
            for p in paths:
                self.registry[p.name].append((kwargs, handler))
                self.paths.append(p)

            return handler

    def path(self, *args, **kwargs):
        return path(*args, view=self.view, **kwargs)

    def view(self, request, **kwargs):
        context = self.context_factory(request, **kwargs)

        for expectations, handler in self.registry[request.resolver_match.url_name]:
            for key, expected_value in expectations.items():
                try:
                    value = cget(context, key)
                except KeyError:
                    break

                if callable(expected_value):
                    if not expected_value(value):
                        break
                else:
                    if value != expected_value:
                        break
            else:
                return handler(context)


NO_DEFAULT = object()


def cget(context, *keys, default=NO_DEFAULT):
    """Helper function to get one or multiple keys from a context.

    If one key is requested, one a single value is returned.
    If multiple keys are requested, a list of values is returned.

    If no default is given and the key does not exist, a KeyError is raised.

    If the requested value is callable, it will be called.
    """
    result = []
    for key in keys:
        if default is NO_DEFAULT:
            value = context[key]
        else:
            value = context.get(key, default)
        if callable(value):
            result.append(value())
        else:
            result.append(value)

    if len(result) == 1:
        return result[0]

    return result
