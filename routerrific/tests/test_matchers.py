import datetime
import json
import uuid
from dataclasses import dataclass
from typing import Annotated, Type

import msgspec
import pytest
from django.http import HttpRequest

from routerrific import Router, route
from routerrific.expr import X
from routerrific.guards import Header
from routerrific.guards.parameter import ParameterGuard
from routerrific.router import RouteConfigurationException, RouteContext


def test_match_path(rf):
    @route("get", "/blog/")
    def blog_list(): ...

    @route("get", r"/blog/(?P<id>\d+)")
    def blog_detail(id: int): ...

    request = rf.get("/blog/123")
    router = Router(
        views=[
            blog_list,
            blog_detail,
        ]
    )

    match = router.match(request)

    assert match is not None
    assert match.view == blog_detail


def test_match_path_django_syntax(rf):
    @route("get", "/blog/<int:id>")
    def blog_detail(id: int): ...

    request = rf.get("/blog/123")
    router = Router(views=[blog_detail])

    match = router.match(request)

    assert match is not None
    assert match.view == blog_detail


def test_match_method(rf):
    @route("get", "/blog/")
    def blog_list(): ...

    request = rf.post("/blog/")
    router = Router(views=[blog_list])

    match = router.match(request)

    assert match is None


def test_parameter_name_mismatch():

    with pytest.raises(RouteConfigurationException) as e:

        @route("get", r"/blog/(?P<post_id>\d+)")
        def view_func(id): ...

        Router(views=[view_func])

    assert "Path parameter named 'post_id' not found in view function" in str(e)


def test_parameter_type_parse_regular(rf):
    @route("get", r"/blog/(?P<id>\d+)")
    def blog_detail(id: int): ...

    router = Router(views=[blog_detail])

    request = rf.get("/blog/123")
    match = router.match(request)

    assert match.args == {"id": 123}


def test_parameter_type_parse_failure(rf):
    @route("get", r"/blog/(?P<id>.*)")
    def blog_detail(id: int): ...

    router = Router(views=[blog_detail])

    request = rf.get("/blog/abc")
    match = router.match(request)

    assert match is None


def test_unsupported_parameter_type(rf):
    class UnsupportedType: ...

    with pytest.raises(RouteConfigurationException) as e:

        @route("get", r"/blog/(?P<id>\d+)")
        def blog_detail(id: UnsupportedType): ...

        Router(views=[blog_detail])

    assert "Unsupported type 'UnsupportedType'" in str(e)


def test_path_parameter_type_default_str(rf):
    @route("get", r"/blog/(?P<id>\d+)")
    def view_func(id): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/123")
    match = router.match(request)

    assert match.args == {"id": "123"}


@pytest.mark.parametrize(
    "path_param,path_cls,url_param,result",
    [
        ("<int:id>", int, "123", 123),
        ("<str:id>", str, "123", "123"),
        ("<path:id>", str, "abc/def", "abc/def"),
        (
            "<uuid:id>",
            uuid.UUID,
            "6ba7b810-9dad-11d1-80b4-00c04fd430c8",
            uuid.UUID("6ba7b810-9dad-11d1-80b4-00c04fd430c8"),
        ),
        (
            "<slug:id>",
            str,
            "abc-def",
            "abc-def",
        ),
    ],
)
def test_path_parameter_django_syntax(rf, path_param, path_cls, url_param, result):
    @route("get", f"/blog/{path_param}")
    def view_func(id: path_cls): ...

    router = Router(views=[view_func])

    request = rf.get(f"/blog/{url_param}")
    match = router.match(request)

    assert match.args == {"id": result}


def test_overload_single_function(rf):
    @route("post", "/blog/")
    @route("get", "/blog/")
    def view_func(): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/")
    match = router.match(request)
    assert match.view is view_func

    request = rf.post("/blog/")
    match = router.match(request)
    assert match.view is view_func


def test_multiple_path_parameters(rf):
    @route("get", r"/shop/(?P<shop_id>\d+)/products/(?P<product_id>\d+)")
    def view_func(shop_id: int, product_id: int): ...

    router = Router(views=[view_func])

    request = rf.get("/shop/123/products/456")
    match = router.match(request)
    assert match.view is view_func
    assert match.args == {"shop_id": 123, "product_id": 456}


def test_body_parameter_regular(rf):

    class Input(msgspec.Struct):
        date: datetime.date

    @route("post", r"/blog/")
    def view_func(x: Input): ...

    router = Router(
        views=[view_func],
        integrations=["routerrific.guards.integrations.msgspec.from_request"],
    )

    request = rf.post(
        "/blog/",
        data=json.dumps({"date": "2023-01-01"}),
        content_type="application/json",
    )
    match = router.match(request)
    assert match.view is view_func
    assert match.args == {"x": Input(date=datetime.date(2023, 1, 1))}


def test_body_parameter_parse_failure(rf):
    class Input(msgspec.Struct):
        a: int

    @route("post", r"/blog/")
    def view_func(x: Input): ...

    router = Router(
        views=[view_func],
        integrations=["msgspec"],
    )

    request = rf.post(
        "/blog/",
        data=json.dumps({"a": "not-an-int"}),
        content_type="application/json",
    )
    match = router.match(request)
    assert match is None


def test_body_parameter_parse_multiple(rf):
    class InputA(msgspec.Struct):
        a: int

    class InputB(msgspec.Struct):
        b: int

    @route("post", r"/blog/")
    def view_func(x: InputA, y: InputB): ...

    router = Router(views=[view_func], integrations=["msgspec"])

    request = rf.post(
        "/blog/",
        data=json.dumps({"a": 1, "b": 2}),
        content_type="application/json",
    )

    match = router.match(request)
    assert match.view is view_func
    assert match.args == {"x": InputA(a=1), "y": InputB(b=2)}


def test_query_parameter_regular(rf):
    @route("get", r"/blog/")
    def view_func(a: int): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/?a=123")
    match = router.match(request)
    assert match.view is view_func
    assert match.args == {"a": 123}


def test_query_parameter_parse_failure(rf):
    @route("get", r"/blog/")
    def view_func(a: int): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/?a=abc")
    match = router.match(request)
    assert match is None


def test_query_parameter_not_found(rf):
    @route("get", r"/blog/")
    def view_func(a: int): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/")
    match = router.match(request)
    assert match is None


@pytest.mark.parametrize(
    "cls,constraint,param,found",
    [
        (int, X >= 0, 123, True),
        (int, X <= 100, 123, False),
        (str, X.length() > 4, "abc", False),
        (str, X.length() < 4, "abc", True),
    ],
)
def test_query_parameter_expr_constraint_int(rf, cls, constraint, param, found):
    @route("get", r"/blog/")
    def view_func(a: Annotated[cls, constraint]): ...

    router = Router(views=[view_func])

    request = rf.get(f"/blog/?a={param}")
    match = router.match(request)
    assert (getattr(match, "view", None) is view_func) == found


@pytest.mark.parametrize(
    "name,constraint,found",
    [
        ("a", X == 123, True),
        ("a", X == 456, False),
        ("b", X == 123, False),
    ],
)
def test_explicit_header_guard_annotation(rf, name, constraint, found):
    @route("get", r"/blog/")
    def view_func(a: Annotated[int, Header, constraint]): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/", headers={name: "123"})

    match = router.match(request)
    assert (match is not None) == found


@pytest.mark.parametrize(
    "value,found",
    [
        ("0", False),
        ("10", True),
    ],
)
def test_multiple_constraints(rf, value, found):
    @route("get", r"/blog/")
    def view_func(a: Annotated[int, X > 0, X < 100, Header]): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/", headers={"a": value})

    match = router.match(request)
    assert (match is not None) == found


def test_custom_matcher(rf):
    @dataclass
    class User:
        id: str

    def user_guard(guard: User, request: HttpRequest, context: RouteContext) -> User:
        return User(id=request.headers["user"])

    @route("get", r"/blog/")
    def view_func(user: User): ...

    router = Router(views=[view_func], integrations=[user_guard])

    request = rf.get("/blog/", headers={"user": "user-id-123"})

    match = router.match(request)
    assert match is not None
    assert match.view is view_func
    assert match.args == {"user": User(id="user-id-123")}


def test_multiple_integrations(rf):
    class UserHeader(msgspec.Struct):
        id: str

    class UserBody(msgspec.Struct):
        id: str

    def user_guard(
        guard: ParameterGuard[UserHeader], request: HttpRequest, context: RouteContext
    ) -> UserHeader:
        return UserHeader(id=request.headers["user"])

    @route("post", r"/blog/")
    def view_func(user_header: UserHeader, user_body: UserBody): ...

    router = Router(views=[view_func], integrations=[user_guard, "msgspec"])

    request = rf.post(
        "/blog/",
        headers={"user": "user-id-123"},
        data=json.dumps({"id": "user-id-456"}),
        content_type="application/json",
    )

    match = router.match(request)
    assert match is not None
    assert match.view is view_func
    assert match.args["user_header"] == UserHeader(id="user-id-123")
    assert match.args["user_body"] == UserBody(id="user-id-456")


def test_integration_variance(rf):
    class User(msgspec.Struct):
        id: str

    class Item(msgspec.Struct):
        id: str

    def from_request(
        guard: ParameterGuard[User],
        request: HttpRequest,
        context: RouteContext,
    ) -> User:
        return User(id=request.headers["user"])

    @route("post", r"/blog/")
    def view_func(user: User, item: Item): ...

    router = Router(views=[view_func], integrations=["msgspec", from_request])

    request = rf.post(
        "/blog/",
        headers={"user": "user-id-123"},
        data=json.dumps({"id": "item-id-456"}),
        content_type="application/json",
    )

    match = router.match(request)
    assert match is not None
    assert match.view is view_func
    assert match.args["user"] == User(id="user-id-123")
    assert match.args["item"] == Item(id="item-id-456")


def test_optional_query_parameter(rf):
    @route("get", r"/blog/")
    def view_func(a: int | None = None): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/")
    match = router.match(request)
    assert match.view is view_func
    assert match.args == {"a": None}


def test_optional_query_parameter_with_default(rf):
    @route("get", r"/blog/")
    def view_func(a: int | None = 123): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/")
    match = router.match(request)
    assert match.view is view_func
    assert match.args == {"a": 123}


def test_optional_header_parameter(rf):
    @route("get", r"/blog/")
    def view_func(a: Annotated[int | None, Header] = None): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/")
    match = router.match(request)
    assert match.view is view_func


def test_optional_header_parameter_with_default(rf):
    @route("get", r"/blog/")
    def view_func(a: Annotated[int | None, Header] = 123): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/")
    match = router.match(request)
    assert match.view is view_func
    assert match.args == {"a": 123}


def test_optional_path_parameter(rf):
    @route("get", r"/((?P<lang>\d+)/)?blog/<int:id>/")
    def view_func(id: int, lang: str | None = None): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/123/")
    match = router.match(request)
    assert match.view is view_func
    assert match.args["id"] == 123
    assert match.args["lang"] is None


def test_optional_path_parameter_with_default(rf):
    @route("get", r"/((?P<lang>\d+)/)?blog/<int:id>/")
    def view_func(id: int, lang: str | None = "en"): ...

    router = Router(views=[view_func])

    request = rf.get("/blog/123/")
    match = router.match(request)
    assert match.view is view_func
    assert match.args["id"] == 123
    assert match.args["lang"] == "en"
