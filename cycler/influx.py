from influxdb_client import InfluxDBClient, Point, WriteOptions

class InfluxWriter:
    def __init__(self, url, token, org, bucket):
        self.bucket = bucket
        self.org = org

        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.write_api = self.client.write_api(
            write_options=WriteOptions(write_type="synchronous")
        )

    def write(self, measurement: str, fields: dict, node_id, cycler_id, setup_id):
        self.tags = {
            "node_id": node_id,
            "cycler_id": cycler_id,
            "setup_id": setup_id,
        }

        p = Point(measurement)
        for k, v in self.tags.items():
            p.tag(k, v)

        for k, v in fields.items():
            if k == "time":
                k = "duration_s"

            if isinstance(v, bool):
                p.field(k, v)

            elif isinstance(v, (int, float)):
                p.field(k, float(v)) 

            elif isinstance(v, str):
                p.field(k, v)

            self.write_api.write(self.bucket, self.org, p)

    def close(self):
        print("[INFLUX] closing...")
        self.client.close()