import logging

from common import log


def test_log_config_has_defaults():
    assert "handlers" in log.log_config
    assert "default" in log.log_config["handlers"]
    assert isinstance(log.logger, logging.Logger)
