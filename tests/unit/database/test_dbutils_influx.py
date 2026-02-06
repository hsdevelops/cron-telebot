from unittest import mock

from database.dbutils import dbutils_influx


def test_save_msg_count_calls_write():
    client = mock.Mock()
    dbutils_influx.save_msg_count(client, 3)
    client.write.assert_called_once()


def test_save_msg_count_handles_exception():
    client = mock.Mock()
    client.write.side_effect = Exception("boom")
    dbutils_influx.save_msg_count(client, 3)
