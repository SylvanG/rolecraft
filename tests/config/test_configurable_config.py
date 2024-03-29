import pytest

from rolecraft.config import config_store as config_store_mod
from rolecraft.config import configurable_config as configurable_config_mod

IncompleteConfigError = config_store_mod.IncompleteConfigError


@pytest.fixture(params=["incomplete", "complete"])
def configurable_config(request, encoder, broker):
    if request.param == "incomplete":
        default = configurable_config_mod.ConfigurableIncompleteQueueConfig(
            encoder=encoder
        )
        return configurable_config_mod.ConfigurableConfig(default=default)
    else:
        default = configurable_config_mod.ConfigurableQueueConfig(
            encoder=encoder, broker=broker
        )
        return configurable_config_mod.ConfigurableDefaultConfig(
            default=default
        )


class TestConfigurableDefaultConfig:
    @pytest.fixture()
    def configurable_config(self, queue_config):
        return configurable_config_mod.ConfigurableDefaultConfig(
            default=queue_config
        )

    def test_add_broker_config_with_defualt_broker(
        self, configurable_config, encoder2
    ):
        broker = configurable_config.default.broker
        configurable_config.add_broker_config(broker, encoder=encoder2)

        store = configurable_config.create_config_store()
        default_queue_config = store.fetcher()
        broker_queue_config = store.fetcher(broker=broker)
        assert default_queue_config != broker_queue_config
        assert default_queue_config == configurable_config.default
        assert broker_queue_config == default_queue_config.replace(
            encoder=encoder2
        )

    @pytest.mark.skip("Haven't implement generic check")
    def test_add_broker_config_with_same_generic_broker(
        self, configurable_config
    ):
        ...

    def test_add_queue_config_without_broker(
        self, configurable_config, encoder2
    ):
        configurable_config.add_queue_config("queue2", encoder=encoder2)

        store = configurable_config.create_config_store()
        default_queue_config = store.fetcher()
        assert default_queue_config == configurable_config.default
        queue_config = store.fetcher("queue2")
        assert queue_config == configurable_config.default.replace(
            encoder=encoder2
        )

    def test_add_queue_config_with_default_broker(
        self, configurable_config, encoder2
    ):
        broker = configurable_config.default.broker
        configurable_config.add_queue_config(
            "queue2", broker=broker, encoder=encoder2
        )

        store = configurable_config.create_config_store()
        default_queue_config = store.fetcher()
        assert default_queue_config == configurable_config.default
        queue_config = store.fetcher("queue2")
        assert queue_config == configurable_config.default.replace(
            encoder=encoder2
        )

    @pytest.mark.skip("Haven't implement generic check")
    def test_add_queue_config_with_same_generic_broker(self):
        ...


def test_add_broker_config(configurable_config, broker2, encoder, middlewares):
    configurable_config.add_broker_config(
        broker2, encoder=encoder, middlewares=middlewares
    )

    store = configurable_config.create_config_store()
    queue_config = store.fetcher(broker=broker2)
    assert queue_config.broker is broker2
    assert queue_config.encoder is encoder
    assert list(queue_config.middlewares) == middlewares
    assert (
        queue_config.wait_time_seconds
        == configurable_config.default.wait_time_seconds
    )


def test_add_queue_config_with_other_broker(
    configurable_config, broker2, encoder, middlewares
):
    configurable_config.add_queue_config(
        "queue2", broker=broker2, middlewares=middlewares
    )

    store = configurable_config.create_config_store()
    queue_config = store.fetcher("queue2", broker=broker2)
    assert queue_config.broker is broker2
    assert queue_config.encoder is encoder
    assert list(queue_config.middlewares) == middlewares


def test_broker_add_queue_config(
    configurable_config, broker, encoder, middlewares, encoder2
):
    configurable_config.add_queue_config(
        "queue1", broker=broker, encoder=encoder, middlewares=middlewares
    )
    broker_config = configurable_config.add_broker_config(
        broker, encoder=encoder, middlewares=[]
    )
    broker_config.add_queue_config("queue2", encoder=encoder2)

    # queue1 config is unchanged
    store = configurable_config.create_config_store()
    queue1_config = store.fetcher("queue1", broker=broker)
    assert queue1_config.broker is broker
    assert queue1_config.encoder is encoder
    assert list(queue1_config.middlewares) == middlewares

    # queue2 config is based on the new broker config
    queue2_config = store.fetcher("queue2", broker=broker)
    assert queue2_config.broker is broker
    assert queue2_config.encoder is encoder2
    assert list(queue2_config.middlewares) == []


class TestIncompleteConfig:
    @pytest.fixture
    def configurable_config(self, encoder):
        default = configurable_config_mod.ConfigurableIncompleteQueueConfig(
            encoder=encoder
        )
        return configurable_config_mod.ConfigurableConfig(default=default)

    def test_set_default(self, configurable_config, broker):
        config = configurable_config.set_default(broker=broker)
        assert config.default.broker is broker

    def test_set_default_keep_original_data(
        self, configurable_config, broker, broker2, encoder2
    ):
        configurable_config.add_queue_config(
            "queue1", broker=broker2, encoder=encoder2
        )
        config = configurable_config.set_default(broker=broker)
        assert config.default.broker is broker

        store = config.create_config_store()
        queue_config = store.fetcher("queue1", broker=broker2)
        assert queue_config.broker is broker2
        assert queue_config.encoder is encoder2

    def test_add_broker_config(
        self, configurable_config, broker, encoder, middlewares
    ):
        configurable_config.add_broker_config(
            broker, encoder=encoder, middlewares=middlewares
        )

        store = configurable_config.create_config_store()

        with pytest.raises(IncompleteConfigError):
            store.fetcher()

    def test_add_queue_config(
        self, configurable_config, broker, encoder, middlewares
    ):
        configurable_config.add_queue_config(
            "queue1", broker=broker, encoder=encoder, middlewares=middlewares
        )

        store = configurable_config.create_config_store()

        with pytest.raises(IncompleteConfigError):
            store.fetcher()

        with pytest.raises(IncompleteConfigError):
            store.fetcher("queue2")
