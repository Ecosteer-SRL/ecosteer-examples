import random
import time
import influxdb_client
from influxdb_client.client.write_api import SYNCHRONOUS
import datetime

bucket = "chain1"
org = "nen"
token = "qGnzB0wzfMx9j6bMyDOUiaoaUIX9hIk9TJxBnoJr5jOgWwlifNw_BV9vxNF7D68XdhYkGPiCStIy9MYNgqssHw=="
# Store the URL of your InfluxDB instance
#url="http://localhost:8086"
url="http://34.154.145.92:8086"


def utc() -> int:
    d = datetime.datetime.utcnow()
    epoch = datetime.datetime(1970,1,1)
    t = (d - epoch).total_seconds()    
    return t


podList = [
    {'pid':'GID001', 'iv': 50},
    {'pid':'GID002', 'iv': 50},
    {'pid':'GID003', 'iv': 50},
    {'pid':'GID004', 'iv': 50},
    {'pid':'GID005', 'iv': 50},
    {'pid':'GID006', 'iv': 50},
    {'pid':'GID007', 'iv': 50},
    {'pid':'GID008', 'iv': 50},
    {'pid':'GID009', 'iv': 50},
    {'pid':'GID010', 'iv': 50},
    {'pid':'GID011', 'iv': 50},
    {'pid':'GID012', 'iv': 50},
    {'pid':'GID013', 'iv': 50},
    {'pid':'GID014', 'iv': 50},
    {'pid':'GID015', 'iv': 50},
    {'pid':'GID016', 'iv': 50},
    {'pid':'GID017', 'iv': 50},
    {'pid':'GID018', 'iv': 50},
    {'pid':'GID019', 'iv': 50},
    {'pid':'GID020', 'iv': 50}
]

client = influxdb_client.InfluxDBClient(
    url=url,
    token=token,
    org=org
)
# Write script
write_api = client.write_api(write_options=SYNCHRONOUS)



initial_value = 50
while True:
    for pod in podList:
        v = pod['iv'] + (5-random.randrange(0,10))
        pod['iv']= v
        #   the following has been checked (OK)
        timestamp = utc()
        print(int(timestamp))

        #   please note:
        #   the time is the number of NANOSECONDS since epoch time (otherwise the write does not work)
        #   see https://docs.influxdata.com/influxdb/v1/write_protocols/line_protocol_reference/
        p = influxdb_client.Point("chain1").tag("PID", pod['pid']).tag("TYPE","EX").field("v", float(v)).time(int(timestamp)*1000000000)
        write_api.write(bucket=bucket, org=org, record=p, time_precision='s')
        print(str(v))
    time.sleep(2)

#https://influxdb-python.readthedocs.io/en/latest/api-documentation.html
#https://influxdb-python.readthedocs.io/en/latest/examples.html?highlight=influxdbclient%20point