from .broker import Broker
from .raw_message import HeaderBytesRawMessage


class BaseBroker(Broker[HeaderBytesRawMessage]):
    def retry(
        self,
        message: HeaderBytesRawMessage,
        queue_name: str,
        *,
        delay_millis: int = 0,
        exception: Exception | None = None,
    ) -> HeaderBytesRawMessage:
        self.ack(message, queue_name)

        # update retries header
        retries = int(message.headers.get("retries") or 0)
        headers = message.headers.copy()
        headers["retries"] = retries + 1

        # enqueue a new message
        new_message = message.replace(id="", headers=headers)
        msg_id = self.enqueue(
            queue_name, new_message, delay_millis=delay_millis
        )
        new_message.id = msg_id

        return new_message
