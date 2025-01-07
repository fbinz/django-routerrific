import pytest
from django.urls import URLResolver, path
from django.urls.resolvers import RegexPattern

from routerific import Router, route
from routerific.router import RouteConfigurationException


def test_default_django_behavior(rf):
    def view_a(): ...
    def view_b(): ...

    resolver = URLResolver(
        RegexPattern("^"),
        [
            path("a", view_a),
            path("b", view_b),
        ],
    )

    match = resolver.resolve("a")

    assert match is not None
    assert match.func == view_a


def test_typed_route(rf):
    def view_a(): ...
    def view_b(): ...

    router = Router()

    resolver = URLResolver(
        RegexPattern("^"),
        [
            router.typed_path("a", view_a),
            path("b", view_b),
        ],
    )

    match = resolver.resolve("a")

    assert match is not None
    assert match.func == view_a
