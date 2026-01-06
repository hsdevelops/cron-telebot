import config
from common import log
from influxdb_client_3 import InfluxDBClient3, Point


measurement = "raw"
field = "message_count"


def save_msg_count(client: InfluxDBClient3, message_count: int) -> None:
    point = Point(measurement).field(field, message_count)
    client.write(record=point)
    log.logger.info(
        f"[INFLUX] Updated influx, measurement={measurement}, field={field}, value={message_count}"
    )
