from unittest import mock

import pytest

from rolecraft import message as message_mod
from rolecraft import middlewares as middlewares_mod
from rolecraft.role_lib import ActionError


@pytest.fixture()
def queue(queue):
    def retry(message, *args, **kwargs):
        message.meta.retries = (message.meta.retries or 0) + 1
        return True

    queue.retry.side_effect = retry
    queue.nack.return_value = True
    return queue


@pytest.fixture()
def retryable(queue):
    return middlewares_mod.Retryable(queue)


@pytest.fixture()
def message():
    msg = mock.MagicMock(message_mod.Message)
    msg.meta = mock.MagicMock(message_mod.Meta)
    msg.meta.retries = None
    return msg


@pytest.fixture()
def exc():
    return ActionError()


def test_retry(retryable, queue, message, exc):
    assert retryable.nack(message=message, exception=exc) is True
    queue.retry.assert_called_once_with(
        message, delay_millis=retryable.base_backoff_millis, exception=exc
    )

    assert retryable.nack(message=message, exception=exc) is True
    queue.retry.assert_called()
    delay_millis = queue.retry.call_args.kwargs.get("delay_millis")
    assert delay_millis > retryable.base_backoff_millis
    assert (
        delay_millis
        <= retryable.base_backoff_millis * retryable.exponential_factor
        + retryable.base_backoff_millis * retryable.jitter_range
    )

    assert retryable.nack(message=message, exception=exc) is True
    queue.retry.assert_called()

    assert retryable.nack(message=message, exception=exc) is True
    queue.nack.assert_called_once_with(message, exception=exc)


def test_max_backoff_millis(retryable, queue, message, exc):
    retryable.max_backoff_millis = 1000

    assert retryable.nack(message=message, exception=exc) is True
    queue.retry.assert_called()
    delay_millis = queue.retry.call_args.kwargs.get("delay_millis")
    assert delay_millis == 1000


def test_should_retry(retryable, queue, message, exc):
    rv = False

    def should_retry(msg, error, retries):
        nonlocal rv
        rv = msg is message and error is exc and retries == 0
        return False

    retryable.should_retry = should_retry

    assert retryable.nack(message=message, exception=exc) is True
    queue.nack.assert_called_once_with(message, exception=exc)
    assert rv is True


def test_raises(retryable, queue, message):
    class MyError(ActionError):
        ...

    class OtherError(ActionError):
        ...

    retryable.raises = (MyError,)

    assert retryable.nack(message=message, exception=MyError()) is True
    queue.nack.assert_called()

    assert retryable.nack(message=message, exception=OtherError()) is True
    queue.retry.assert_called()