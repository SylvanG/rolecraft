import collections.abc
import dataclasses
import functools
from .middleware import Middleware
from .retryable import Retryable


@dataclasses.dataclass(init=False, eq=False, order=False, repr=False)
class MiddlewareList[M: Middleware](collections.abc.MutableSequence[M]):
    _middlewares: list[Middleware]
    retryable: Retryable | None = None

    def __init__(self, middlewares: list[Middleware] = None) -> None:
        middlewares = middlewares or []

        self._set_field("_middlewares", middlewares)

        for middleware in middlewares:
            self._set_middleware(middleware)

    def _set_middleware(self, middleware: Middleware):
        field_name = self._field_name_for(middleware)
        self._set_field(field_name, middleware)

    def _remove_middleware(self, middleware: Middleware):
        field_name = self._field_name_for(middleware)
        self._set_field(field_name, None)

    def _field_name_for(self, middleware: Middleware) -> str:
        if isinstance(middleware, Retryable):
            return "retryable"
        raise TypeError(f"Unknonw middleware type: {middleware}")

    def _remove_middleware_by_name(self, name: str):
        middleware = getattr(self, name)
        assert middleware, f"middleware doesn't exist for {name}"
        self._middlewares.remove(middleware)
        self._set_field(name, None)

    def _set_field(self, name, value):
        super().__setattr__(name, value)

    @functools.cached_property
    def _field_names(self) -> set[str]:
        return set((field.name for field in dataclasses.fields(self)))

    def __setattr__(self, name, value):
        if name == "_middlewares":
            raise ValueError("_middlewares update is not allowed.")

        if name in self._field_names:
            if not getattr(self, name):
                raise ValueError(
                    "Update non-existing middleware is not allowed. "
                    "Please use append or insert method."
                )
            if value is None:
                self._remove_middleware_by_name(name)
                return
            elif self._field_name_for(value) != name:
                raise TypeError(f"Middleware type error for {name}: {value}")

        super().__setattr__(name, value)

    # -- MutableSequence implmenetation --
    def insert(self, index: int, value: M) -> None:
        field_name = self._field_name_for(value)
        if getattr(self, field_name):
            raise ValueError(f"Middleware {field_name} exists")
        self._set_field(field_name, value)
        return self._middlewares.insert(index, value)

    def __setitem__(self, index: int, value: M) -> None:
        old_field_name = self._field_name_for(self._middlewares[index])
        field_name = self._field_name_for(value)
        if old_field_name != field_name:
            if getattr(self, field_name):
                raise ValueError(f"Middleware {field_name} exists")
            self._set_field(old_field_name, None)
        self._set_field(field_name, value)
        self._middlewares[index] = value

    def __delitem__(self, index: int) -> None:
        middleware = self._middlewares[index]
        self._remove_middleware(middleware)

    def __getitem__(self, index: int) -> M:
        return self._middlewares[index]

    def __len__(self) -> int:
        return len(self._middlewares)