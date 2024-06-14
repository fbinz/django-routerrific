from django_routerrific import Router, route


def test_empty_router(rf):
    router = Router()

    response = router.dispatch(rf.get("/"))
    assert response.status_code == 404


def test_dispatch_regular(rf):
    result = {}

    @route("get", "/blog/")
    def blog_list(): ...

    @route("get", r"/blog/(?P<id>\d+)")
    def blog_detail(id: int):
        return result

    router = Router(views=[blog_list, blog_detail])
    response = router.dispatch(rf.get("/blog/123"))

    assert response is result


def test_dispatch_not_found(rf):
    @route("get", "/blog/")
    def blog_list(): ...

    router = Router(views=[blog_list])
    response = router.dispatch(rf.get("/blub/123"))
    assert response.status_code == 404
