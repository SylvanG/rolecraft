from typing import Protocol, Unpack

from rolecraft.queue import QueueConfig, QueueConfigOptions


class ConfigFetcher(Protocol):
    def __call__[M](
        self,
        queue_name: str | None = None,
        **kwds: Unpack[QueueConfigOptions[M]],
    ) -> QueueConfig[M]:
        """Fetches QueueConfig for a specific queue. If the queue name is None, it will return the default QueueConfig."""
        ...
