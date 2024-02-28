#   inputProvider:
#     path:   '/home/ecosteer/monitor/ecosteer/dop/provider/presentation/input/pres_input_mqtt.py'
#     class: 'inputMqttPaho'
#     configuration: 'h=10.170.30.66;p=1883;t=test_topic;rc=10;ka=60;q=1;tout=10;prf=grz_;'

#   auth:   graz
#   vers:   0.1 
#   date:   28/Feb/2024
#   comp:   ecosteer


#import pdb

import sys
#sys.path.append('../..')

from typing import Tuple, Callable
import json
import traceback
import yaml

#   import from packages and modules within the ecosteer project (ecosteer is the root folder)
from common.python.error import DopError
from common.python.event import DopEventHeader, DopEventPayload, DopEvent
from common.python.utils import DopUtils
from common.python.threads import DopStopEvent

from Chain1ToInfluxdb import Chain1ToInfluxdb



class UserDataClass:
    """
        just to show an example of using userdata in the mqtt input provider
        follow the rabbit
    """

    def __init__(self):
        self.influxdb = None
        self.influxdb_options = {}

    def tracefun(self, called: str):
        print('\x1b[1;91m' + 'UserDataClass [' + called + ']' + '\x1b[0m')

    def tracevent(self, eve: DopEvent):
        print('\x1b[1;32m' + str(eve) + '\x1b[0m')

    
        



#   global stop event, to control async ops in the main and in the provider
globalStopEvent = DopStopEvent()


globalUserData: UserDataClass = UserDataClass()


def error_callback(err: DopError, userdata):

    #   example: how to use userdata
    ghost: UserDataClass = userdata
    ghost.tracefun('error_callback')

    print("err: " + str(err.code) + " msg: " + err.msg)

    #   the following is just a suggestion about how to react to non recoverable errors
    if err.isRecoverable()==False:
        globalStopEvent.stop()
    return

def data_callback(message_topic: str, message_payload: str, userdata):
    print(message_payload)

    #   userdata holds the property 'influxdb' that has to be used to propagate the datapoints to influxdb
    #   the message has to be processed by the Chain1ToInfluxdb object
    #   the input message has to be a json string like this one (please note that the arrays ea and er
    #   must contain 96 values)
    #   '{"category": "CHAIN1", "product_id":"931cdeca-0258-4421-b84a-d4fb65aacccd","timestamp":1709052091, "ea":[1,2,3,4,5], "er":[10,11,12,13,14,15]}'

    #   example: how to use userdata
    ghost: UserDataClass = userdata
    ghost.tracefun('data_callback')

    #   the influx instance is created opened and closed every time
    influx = Chain1ToInfluxdb(ghost.influxdb_options)

    #   propagate the datapoints to influxdb
    #influx = ghost['influxdb']
    err: DopError = influx.open()
    if err.isError():
        print('ERR=' + str(err.code))
    else:
        err = influx.write(message_payload)

    if err.isError():
        print('ERR=' + str(err.code))
    
    influx.close()
    return

def main(confFilePath: str) -> DopError:

    #pdb.set_trace()
    tupleConfiguration = DopUtils.parse_yaml_configuration(confFilePath)
    if tupleConfiguration[0].isError():
        return tupleConfiguration[0]
    
    configuration_dict: dict = tupleConfiguration[1]
    if ('inputProvider' in configuration_dict) == False:
        return (DopError(1,'missing inputProvider key from conf file'))
    
    if ('influxdb' in configuration_dict) == False:
        return (DopError(2,'missing influxdb key from conf file'))
    
    #   get the influxdb configuration string
    influxdb_conf_tuple = DopUtils.config_to_dict(configuration_dict['influxdb']['configuration'])
    if influxdb_conf_tuple[0].isError():
        return influxdb_conf_tuple[0]
    
    
    #   influxdb configuration available
    #   the influxdb configuration is a dict that has to contain the following properties:
    #   bucket
    #   org
    #   token
    #   url
    #pdb.set_trace()
    influxdb_configuration: dict = influxdb_conf_tuple[1]
    if ('token' in configuration_dict['influxdb']) == False:
        print('missing token property')
        exit(5)
    #   add the token property tp the nfluxdb options
    influxdb_configuration['token']=configuration_dict['influxdb']['token']
    #   assign the influxdb options to the user data property (influxdb_options)
    globalUserData.influxdb_options = influxdb_configuration

    #   let's use the configuration to open influxdb
    #   to check if everythin is ok
    influx = Chain1ToInfluxdb(influxdb_configuration)
    err: DopError = influx.open()
    if err.isError():
        print('ERR='+str(err.code))
        exit(err.code)
    influx.close()


    configuration: dict = configuration_dict['inputProvider']

    tupleLoadProvider = DopUtils.load_provider(configuration)
    if tupleLoadProvider[0].isError():
        return tupleLoadProvider[0]
    provider = tupleLoadProvider[1]
    #   the provider has been loaded, now it has to be initialized/configured

    #=================================================================================
    #   before initializing the provider, we need to set the any available callback
    #=================================================================================
    provider.set_on_data_callback(data_callback)
    provider.set_on_error_callback(error_callback)
    #   attach the stop event
    provider.attach_stop_event(globalStopEvent)
    #   set userdata
    provider.set_userdata(globalUserData)

    confstring: str = configuration['configuration']
    err: DopError = provider.init(confstring)
    if err.code != 0:
        return err


    print('opening provider')
    err: DopError = provider.open()
    if err.isError():
        print(err.msg)
        return err
    
    print('provider open')
    
    provider.read()

    print('press enter to stop')

    
    sys.stdin.readline()
   
    globalStopEvent.stop()
    

    print('closing provider')
    provider.close()

    influx.close()

    return DopError()

if __name__ == "__main__":
    print('executing')
    err: DopError = main(sys.argv[1])
    if err.isError():
        print(err.msg)
