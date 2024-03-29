import dataclasses
from unittest import mock

import pytest

from rolecraft.config import middleware_list as middleware


@pytest.fixture()
def empty_middleware_list():
    return middleware.MiddlewareList()


@pytest.fixture()
def retryable():
    return middleware.Retryable()


@pytest.fixture()
def middleware_list(retryable):
    return middleware.MiddlewareList([retryable])


@dataclasses.dataclass(init=False, eq=True, order=False, repr=False)
class MiddlewareList(middleware.MiddlewareList):
    middleware2: mock.MagicMock | None = None
    middleware3: mock.MagicMock | None = None

    def name_for(self, middleware) -> str | None:
        if getattr(middleware, "_name", None) in (2, 3):
            return "middleware" + str(middleware._name)
        return super().name_for(middleware)


@pytest.fixture()
def middleware2():
    middleware = mock.MagicMock()
    middleware._name = 2
    return middleware


@pytest.fixture()
def middleware3():
    middleware = mock.MagicMock()
    middleware._name = 3
    return middleware


@pytest.fixture()
def middleware_no_name():
    middleware = mock.MagicMock()
    middleware._name = 4
    return middleware


@pytest.fixture()
def two_middlewares_list(middleware2, middleware3):
    return MiddlewareList([middleware2, middleware3])


@pytest.fixture()
def three_middlewares_list(retryable, middleware2, middleware3):
    return MiddlewareList([retryable, middleware2, middleware3])


def test_update_non_existing_middleware(empty_middleware_list, retryable):
    with pytest.raises(ValueError):
        empty_middleware_list.retryable = retryable


def test_append_a_new_middleware(empty_middleware_list, retryable):
    empty_middleware_list.append(retryable)
    assert empty_middleware_list.retryable is retryable
    assert empty_middleware_list[0] is retryable
    assert empty_middleware_list[-1] is retryable
    assert len(empty_middleware_list) == 1


def test_len(empty_middleware_list):
    assert len(empty_middleware_list) == 0


def test_iter(middleware_list):
    assert len(list(middleware_list)) == 1


def test_modify_a_middleware(middleware_list):
    middleware_list.retryable = None
    assert len(middleware_list) == 0


def test_del(middleware_list):
    del middleware_list[0]
    assert len(middleware_list) == 0
    assert middleware_list.retryable is None


def test_set_with_index(retryable, middleware2, middleware3):
    middlewares = MiddlewareList([retryable, middleware2])
    assert middlewares.retryable
    assert middlewares.middleware2

    middlewares[1] = middleware3
    assert not middlewares.middleware2
    assert middlewares.middleware3 is middleware3

    with pytest.raises(ValueError):
        middlewares[1] = retryable


def test_middleware_without_name(
    middleware_no_name, retryable, middleware2, middleware3
):
    middleware_list = [retryable, middleware_no_name, middleware2]
    middlewares = MiddlewareList(middleware_list)
    assert len(middlewares) == 3
    assert middlewares.retryable
    assert middlewares.middleware2
    assert list(middlewares) == middleware_list

    middlewares.append(middleware_no_name)
    assert len(middlewares) == 4

    middlewares[1] = middleware3
    assert len(middlewares) == 4
    assert middlewares[1] is middleware3
    assert middlewares.middleware3 is middleware3


def test_slice(three_middlewares_list):
    assert isinstance(three_middlewares_list[0:1], MiddlewareList)
    middlewares = three_middlewares_list[0:1] + three_middlewares_list[2:]
    assert len(middlewares) == 2
    assert isinstance(middlewares, MiddlewareList)


def test_empty(empty_middleware_list, middleware_list):
    assert not empty_middleware_list
    assert middleware_list


class TestAdd:
    @pytest.fixture(params=["iadd", "add", "radd"])
    def middlewares_list(self, request, two_middlewares_list, retryable):
        if request.param == "iadd":
            two_middlewares_list += [retryable]
            return two_middlewares_list
        elif request.param == "add":
            return two_middlewares_list + [retryable]
        elif request.param == "radd":
            return [retryable] + two_middlewares_list
        else:
            raise RuntimeError()

    def test_add(self, request, middlewares_list, retryable):
        assert len(middlewares_list) == 3
        assert isinstance(middlewares_list, MiddlewareList)
        assert (
            middlewares_list[-1] is retryable
            or middlewares_list[0] is retryable
        )
        assert middlewares_list.retryable is retryable
