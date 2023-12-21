from .queue import Queue
from .config import ConfigFetcher
from .broker import Broker, default_broker


class QueueBuilder:
    def __init__(
        self,
        config_fetcher: ConfigFetcher,
        queue_names: list[str] | None = None,
        queues: list[Queue] | None = None,
    ):
        self.queue_names = queue_names
        self.queues = queues
        self.config_fetcher = config_fetcher

    def build(self) -> list[Queue]:
        return self._build_queues(self.queue_names, self.queues)

    def _build_queues(self, queue_names, queues) -> list[Queue]:
        all_queues = []

        if queue_names:
            all_queues.extend(
                self._build_queues_with_default_broker(queue_names)
            )

        all_queues.extend(queues)

        if not all_queues:
            all_queues.append(self._get_default_queue())

        return [self._wrap(q) for q in all_queues]

    def _build_queues_with_default_broker(self, queue_names):
        broker = self._get_default_broker()
        for queue_name in queue_names:
            config = self.config_fetcher(queue_name, broker)
            yield Queue(name=queue_name, broker=broker, encoder=config.encoder)

    def _get_default_queue(self) -> Queue:
        return Queue(name="default", broker=self._get_default_broker())

    def _get_default_broker(self) -> Broker:
        assert default_broker
        return default_broker

    def _wrap(self, queue: Queue) -> Queue:
        config = self.config_fetcher(queue.name, queue.broker)
        for middleware in config.middlewares:
            queue = middleware(queue)
            assert isinstance(queue, Queue)
        return queue
