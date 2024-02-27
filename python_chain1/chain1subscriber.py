import  time
import  json

import  influxdb_client
from    influxdb_client.client.write_api import SYNCHRONOUS
import  datetime

from    common.python.error import DopError

#   errors constants
ERR_OPEN_EXCEPTION: int                         = 100
ERR_INFLUXDB_INSTANTIATION_EXCEPTION: int       = 101
ERR_OPTION_MISSING: int                         = 102
ERR_INVALID_JSON: int                           = 103
ERR_MISSING_CHAIN1_PROPERTY: int                = 104
ERR_NOT_OPENED: int                             = 105
ERR_WRITING_POINT: int                          = 106


class Chain1ToInfluxdb:
    def __init__(self, options: dict):
        """
        option is a dictionary declaring the following parameters necessary to integrate
        with an Influxdb server:
        
        bucket                      the name of the bucket to write to
        org                         the name of the organization the writer belongs to
        token                       the token assigned to the writer (a user that belongs to the declared organization)
        url                         the url where the Influxdb is found

        example:
        options = {
        "bucket": "chain1",
        "org":"nen",
        "token":"qGnzB0wzfMx9j6bMyDOUiaoaUIX9hIk9TJxBnoJr5jOgWwlifNw_BV9vxNF7D68XdhYkGPiCStIy9MYNgqssHw==",
        "url":"http://34.154.145.92:8086"
        }
        """
        self.__options = options
        self.__is_open = False
        self.__influxdb = None
        self.__write_api = None

    def __check_options(self) -> DopError:
        for property in ['bucket', 'org', 'token', 'url']:
            if not (property in self.__options):
                return DopError(ERR_OPTION_MISSING, property)
        return DopError(0)


    def __open(self) -> DopError:
        err: DopError = self.__check_options()
        if err.isError():
            return err
        
        #   options are valid, instantiate influxdb
        if self.__is_open == True:
            self.close()

        try:
            #   here we are sure that in the options we have all what we need

            self.__influxdb = influxdb_client.InfluxDBClient(
                url     =self.__options['url']
            ,   token   =self.__options['token']
            ,   org     =self.__options['org']
            )
            self.__write_api = self.__influxdb.write_api(write_options=SYNCHRONOUS)
            self.__is_open = True

        except:
            return DopError(ERR_INFLUXDB_INSTANTIATION_EXCEPTION)
        
        return err

        
    def open(self) -> DopError:
        ret: DopError = DopError(0)
        try:
            ret: DopError = self.__open()    
        except:
            return DopError(ERR_OPEN_EXCEPTION)
        return ret
    
    def close(self) -> DopError:
        ret: DopError = DopError(0)
        self.__is_open = False
        self.__write_api = None
        self.__influxdb = None
        return ret

    
    def write(self, chain1_json: str) -> DopError:
        """
        this method will propagate the chain1 frame (holding 96 v for AE and 96 v for RE)
        into 96x2 measurements to be propagated to influxdb

        the input chain1_json is a json string like  '{"ea":[1,2,3],"er":[3,4,5]}'
        '{
        "category": “CHAIN1”,
        "product_id": "marketplace PID",
        "timestamp": "UTC",
        "ea": [val1, ..., val96],
        "er": [val1, …, val96]
        }'

        """

        json_object: dict = {}
        try:
            json_object = json.loads(chain1_json)
        except json.JSONDecodeError as e:
            print("Invalid JSON syntax:", e)
            return DopError(ERR_INVALID_JSON)
        
        #   the json frame has been parsed
        #   now check if we have what we need
        for property in ['category', 'product_id', 'timestamp', 'ea', 'er']:
            if not (property in json_object):
                return DopError(ERR_MISSING_CHAIN1_PROPERTY,property)
        
        #   the JSON object is a valid CHAIN1 json OBJ, continue
        err: DopError = DopError(0)
        if self.__is_open == False:
            err = self.open()
        if err.isError():
            return err
        
        
        err = self.write_serie(json_object['product_id'],'EA',int(json_object['timestamp']),json_object['ea'])
        if err.isError():
            return err
        
        err = self.write_serie(json_object['product_id'],'ER',int(json_object['timestamp']),json_object['er'])
        return err


    def write_point(self, product_id, data_type, timeofpoint, value) -> DopError:
        #   please note:
        #   the time is the number of NANOSECONDS since epoch time (otherwise the write does not work)
        #   see https://docs.influxdata.com/influxdb/v1/write_protocols/line_protocol_reference/
        if self.__is_open == False:
            return DopError(ERR_NOT_OPENED)
        
        
        #print ("@@ PID=" + product_id + ", TYPE=" + data_type + ", TIME=" + str(timeofpoint) + ", V=" + str(value))
        try:
            bucket = self.__options['bucket']
            org = self.__options['org']
            p = influxdb_client.Point(bucket).tag("PID", product_id).tag("TYPE",data_type).field("v", float(value)).time(int(timeofpoint)*1000000000)
            self.__write_api.write(bucket=bucket, org=org, record=p, time_precision='ns')
        except Exception as e:
            print(e)
            return DopError(ERR_WRITING_POINT)
        
        return DopError(0)



    def write_serie(self
        ,   product_id
        ,   data_type
        ,   start_of_series
        ,   values: list
        ) -> DopError:

        err: DopError = DopError(0)
        quarterly_step = 900    #   number of seconds in 15 mnutes
        timeofpoint = start_of_series
        for v in values:
            err = self.write_point(product_id, data_type, timeofpoint, v)
            if err.isError():
                return err
            timeofpoint = timeofpoint + quarterly_step
        return err
        

        

def utc() -> int:
    d = datetime.datetime.utcnow()
    epoch = datetime.datetime(1970,1,1)
    t = (d - epoch).total_seconds()    
    return t



if __name__ == "__main__":
    
    options: dict = {
    "bucket": "chain1",
    "org":"nen",
    "token":"RwzwWETiNYYsAn1W6rGsYJnjL1gxV_Xid9jEuA006f5U0ASAwsNiqZJBCP7HQwSFA1rTrf2TqfPsrPHe-zTlHg==",
    "url":"http://34.88.70.190:8086"
    }

    inf = Chain1ToInfluxdb(options)
    err: DopError = inf.open()
    if err.isError():
        print('ERR='+str(err.code))
        exit(err.code)

    while True:
        now = utc()
        json_string = '{"category": "CHAIN1", "product_id":"931cdeca-0258-4421-b84a-d4fb65aacccd","timestamp":'
        json_string = json_string + str(now)
        json_string = json_string + ', "ea":[1,2,3,4,5], "er":[10,11,12,13,14,15]}'

        #pdb.set_trace()
        err = inf.write(json_string)
        inf.close()
        print('ERR=' + str(err.code))
        time.sleep(20)





        
        
        
        



