import config
from common import log
from influxdb_client_3 import InfluxDBClient3, Point

client = InfluxDBClient3(
    host=config.INFLUXDB_HOST,
    token=config.INFLUXDB_TOKEN,
    org=config.INFLUXDB_ORG,
    database=config.INFLUXDB_BUCKET,
)

measurement = "raw"
field = "message_count"


def save_msg_count(message_count: int) -> None:
    point = Point(measurement).field(field, message_count)
    client.write(record=point)
    log.log_influx_resp(measurement, field, message_count)
