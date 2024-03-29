import abc
import functools
import logging
from collections.abc import Callable, Mapping
from typing import Any, Concatenate

from rolecraft.broker import Broker, EnqueueOptions
from rolecraft.queue.encoder import Encoder
from rolecraft.queue.message import Message

__all__ = ["MessageQueue", "EnqueueOptions"]

logger = logging.getLogger(__name__)


# refer to:
# https://stackoverflow.com/questions/70329648/type-friendly-delegation-in-python
def copy_method_signature[CLS, **P, T](
    source: Callable[Concatenate[Any, str, P], T],
) -> Callable[[Callable[..., T]], Callable[Concatenate[CLS, P], T]]:
    def wrapper(target: Callable[..., T]) -> Callable[Concatenate[CLS, P], T]:
        @functools.wraps(target)
        def wrapped(self: CLS, /, *args: P.args, **kwargs: P.kwargs) -> T:
            return target(self, *args, **kwargs)

        return wrapped

    return wrapper


# Omit `queue_name: str | None` from the Broker's method signature
def copy_msg_method_signature[CLS, **P, T](
    source: Callable[Concatenate[Any, Message, str | None, P], T],
) -> Callable[[Callable[..., T]], Callable[Concatenate[CLS, Message, P], T]]:
    def wrapper(
        target: Callable[..., T],
    ) -> Callable[Concatenate[CLS, Message, P], T]:
        @functools.wraps(target)
        def wrapped(
            self: CLS, /, message: Message, *args: P.args, **kwargs: P.kwargs
        ) -> T:
            return target(self, message, *args, **kwargs)

        return wrapped

    return wrapper


class MessageQueue[RawMessage](abc.ABC):
    def __init__(
        self,
        name: str,
        broker: Broker[RawMessage],
        encoder: Encoder[RawMessage],
        wait_time_seconds: int | None = None,
        settings: Mapping[str, Any] | None = None,
    ) -> None:
        self.name = name
        self.broker = broker
        self.encoder = encoder
        self.wait_time_seconds = wait_time_seconds
        self.settings = settings or {}

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.broker})"

    @copy_method_signature(Broker[Message].enqueue)
    def enqueue(self, message: Message, *args, **kwargs):
        raw_message = self.encoder.encode(message)
        return self.broker.enqueue(self.name, raw_message, *args, **kwargs)

    @copy_method_signature(Broker[Message].block_receive)
    def block_receive(self, *args, **kwargs):
        """If the wait_time_seconds is None, it will be default value of the
        queue."""
        kwargs.setdefault("wait_time_seconds", self.wait_time_seconds)
        future = self.broker.block_receive(self.name, *args, **kwargs)
        return future.transform(self._decode_messages)

    @copy_method_signature(Broker[Message].receive)
    def receive(self, *args, **kwargs):
        return self._decode_messages(
            self.broker.receive(self.name, *args, **kwargs)
        )

    def _decode_messages(self, messages: list[RawMessage]) -> list[Message]:
        decoded = []
        for msg in messages:
            try:
                decoded.append(self.encoder.decode(msg, queue=self))
            except Exception as e:
                logger.error(
                    "Decode error for message %s",
                    getattr(msg, "id", msg),
                    exc_info=e,
                )
        return decoded

    @copy_method_signature(Broker[Message].qsize)
    def qsize(self, *args, **kwargs):
        return self.broker.qsize(self.name, *args, **kwargs)

    @copy_msg_method_signature(Broker[Message].ack)
    def ack(self, message: Message, *args, **kwargs):
        return self.broker.ack(
            self.encoder.encode(message), self.name, *args, **kwargs
        )

    @copy_msg_method_signature(Broker[Message].nack)
    def nack(self, message: Message, *args, **kwargs):
        return self.broker.nack(
            self.encoder.encode(message), self.name, *args, **kwargs
        )

    @copy_msg_method_signature(Broker[Message].requeue)
    def requeue(self, message: Message, *args, **kwargs):
        return self.broker.requeue(
            self.encoder.encode(message), self.name, *args, **kwargs
        )

    @copy_msg_method_signature(Broker[Message].retry)
    def retry(self, message: Message, *args, **kwargs):
        return self.broker.retry(
            self.encoder.encode(message), self.name, *args, **kwargs
        )

    def close(self):
        return self.broker.close()

    def prepare(self, **kwargs):
        options = dict(self.settings)
        options.update(kwargs)
        return self.broker.prepare_queue(self.name, **options)
