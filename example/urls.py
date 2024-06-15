from typing import Annotated

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, re_path

from routerrific import Router, route
from routerrific.expr import X
from routerrific.router import include


@route("get", "/blog/")
def list_view():
    return HttpResponse("Hello World")


@route("get", "/blog/<str:id>")
def detail_view(
    id: Annotated[str, X.length() > 4],
):
    return HttpResponse(f"Hello {id}")


views = [
    list_view,
    detail_view,
]


router = Router(
    [
        include("example.urls.views"),
    ]
)


urlpatterns = [
    path("admin/", admin.site.urls),
    re_path("^blog", router.dispatch, name="blog"),
]
