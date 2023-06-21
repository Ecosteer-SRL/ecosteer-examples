#   ver:    1.0
#   date:   03/03/2023
#   author: georgiana-bud


#   ver:    1.1 
#   date:   17/05/2023
#   author: georgiana-bud


#   VER 1.1
#   change locking, printing and publish mechanisms
#   add indication of how to use new mqtt output client (not a dynamically loaded provider)

import argparse
import datetime 
import os
import signal
import time
from threading import Event, Thread, Lock

from externals.CO2Meter import *
from common.python.utils import DopUtils
from common.python.error import DopError
from common.python.threads import DopStopEvent
#from provider.mqtt_output import MqttClient

#   usage: sensor.py -c configFile.yaml

# GLOBAL VARIABLES
global_stop_event: DopStopEvent
global_print_lock: Lock

def get_args(argl = None):
    
    parser = argparse.ArgumentParser(description="Sensor stream program.")
    parser.add_argument("-c", "--config",
        help = "The configuration file for the main program.", 
        required = True)
    
    return parser.parse_args()


def signalHandlerDefault(signalNumber, frame):
    print('Received:', signalNumber)

def progstop():
    print('Exiting ...')
    global_stop_event.stop()

def signalHandlerExit(signalNumber, frame):
    progstop()

def signalManagement():
    signal.signal(signal.SIGTERM, signalHandlerExit)
    signal.signal(signal.SIGINT, signalHandlerExit)
    signal.signal(signal.SIGQUIT, signalHandlerExit)




class PublisherUserdata:
    def __init__(self):
        self._output_provider = None

        
    @property
    def output_provider(self):
        return self._output_provider 

    @output_provider.setter
    def output_provider(self, output_provider):
        self._output_provider = output_provider 



def synced_print(msg: str):
    
    with global_print_lock:
        print(msg)

def publish(payload: str, userdata) -> DopError:
    publisher_userdata: PublisherUserdata = userdata
    output_provider = publisher_userdata.output_provider
    
    err = output_provider.write(payload)

    if err.isError():
        print(f"pub failure")
        return DopError(2, "pub failure")
    else:
        print(f"pub ok")
    return DopError()

    
    """
    # A logic that retries to publish the message can be implemented here e.g.
    while success == False:
        err = output_provider.write(payload)
            
        if err.isError():
            synced_print("pub failure")
            time.sleep(2)
        else:
            success = True
            synced_print("pub ok")

    return DopError()
    """



def thread_co2(configuration: dict, userdata: PublisherUserdata, verbose):
    run: int = int(configuration['run'])
    if run!=1:
        return

    co2_driver = configuration['driver']
    sleep: int     = int(configuration['sleep'])

    sensor = CO2Meter(co2_driver)

    while True:   
        if global_stop_event.is_exiting():
            break
        
        d = sensor.get_data()
        d['now']=str(datetime.datetime.now())

        #   send to broker
        payload: str = str(d)
        synced_print(payload)

        err = publish(payload, userdata)

        global_stop_event.wait(sleep)



def main(args) -> DopError:

    #   Parse arguments
    config_file = args.config 


    if not os.path.exists(config_file):
        return DopError(101,"Configuration file does not exist")


    #   prog default
    verbose: bool = False

    #   co2 driver default/init
    co2_driver: str = ""
    co2_sleep: int = 5
    
    userdata: PublisherUserdata = None

    # ========================================================
    #   Configuration file
    # ========================================================
    err, conf = DopUtils.parse_yaml_configuration(config_file)
    if err.isError():
        return err

    #   CO2
    co2_c = conf['co2']
    err, co2_conf = DopUtils.config_to_dict(co2_c['configuration'])
    if err.isError():
        return err

    #   mandatory args
    if 'driver' in co2_conf:
        co2_driver = co2_conf['driver']
    else:
        return DopError(10,'Missing arg: co2: driver') 

    if 'sleep' in co2_conf:
        co2_sleep = int(co2_conf['sleep'])

    #   PROG
    prog_c = conf['prog']
    err, prog_conf = DopUtils.config_to_dict(prog_c['configuration'])
    if err.isError():
        return err
    
    if 'v' in prog_conf:
        verbose = (prog_conf['v'] == '1')

    #   OUTPUT PROVIDER


#    outputProvider_c = conf['mqtt']
#    outputProvider_conf = outputProvider_c['configuration']
#    err, outputProv_conf_dict = DopUtils.config_to_dict(outputProvider_conf)

#    output_provider = MqttClient()
  
    outputProvider_dict = conf['outputProvider']
    err, output_provider = DopUtils.load_provider(outputProvider_dict)
    if err.isError():
        return err


    outputProvider_conf = outputProvider_dict['configuration']
    err, outputProv_conf_dict = DopUtils.config_to_dict(outputProvider_conf)


    
    tv, host = DopUtils.config_get_string(outputProv_conf_dict, ['h'], None)
    tv, port = DopUtils.config_get_int(outputProv_conf_dict, ['p'], 1883)
    tv, topic = DopUtils.config_get_string(outputProv_conf_dict, ['t'], None)
    prov_err = output_provider.init(outputProvider_conf)

 
    if prov_err.isError():
        return prov_err

    output_provider.attach_stop_event(global_stop_event)
    prov_err = output_provider.open()
    if prov_err.isError():
        return prov_err

    # Userdata 
    userdata = PublisherUserdata()
    userdata.output_provider = output_provider


    if verbose:
        print(f'Broker host       : {host}')
        print(f'Broker port       : {port}')
        print(f'Broker topic     : {topic}') 

        print(f'CO2 driver        : {co2_driver}')
        print(f'CO2 sleep         : {co2_sleep}')


    # ====================================================================================
    # Main Program
    # ====================================================================================

    co2_t = Thread(target=thread_co2, args=(co2_conf, userdata, verbose))
    co2_t.start()
    time.sleep(1)
    
    co2_t.join()

    prov_err = output_provider.close()
    return prov_err

if __name__ == "__main__":
    
    global_stop_event = DopStopEvent()
    global_print_lock = Lock()
    signalManagement()

    error: DopError = main(get_args())
    print(error)
