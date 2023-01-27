#   ver:    1.0
#   date:   27/01/2023
#   author: georgiana-bud

import sys

import datetime
import time
import signal
from threading import Event, Thread, Lock

from externals.CO2Meter import *
from common.python.utils import DopUtils
from common.python.error import DopError
from common.python.threads import DopStopEvent

#   usage: sensor.py configFile.yaml

global_stop_event: DopStopEvent

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
        self._print_lock: Lock = Lock()
        self._publish_lock: Lock = Lock()

        
    @property
    def output_provider(self):
        return self._output_provider 

    @output_provider.setter
    def output_provider(self, output_provider):
        self._output_provider = output_provider 

    @property 
    def publish_lock(self):
        return self._publish_lock 

    @property
    def print_lock(self):
        return self._print_lock



def synced_print_callback(msg: str, userdata):
    publisher_userdata: PublisherUserdata = userdata 
    print_lock = publisher_userdata.print_lock 
    print_lock.acquire()
    try:
        print(msg)
    finally:
        print_lock.release()    


def synced_publish_callback(payload: str, userdata) -> DopError:
    publisher_userdata: PublisherUserdata = userdata
    output_provider = publisher_userdata.output_provider
    publish_lock = publisher_userdata.publish_lock 
    publish_lock.acquire() 
    try: 
        err = output_provider.write(payload)
    finally:
        publish_lock.release()

    return err

def thread_co2(configuration: dict, userdata, verbose):
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
        success: bool = False
        while success == False:
            err = synced_publish_callback(payload, userdata)
            if err.isError():
                synced_print_callback("pub failure", userdata)
                time.sleep(2)
            else:
                success = True
                synced_print_callback("pub ok", userdata)
                

        if verbose:
            synced_print_callback(payload, userdata)
        global_stop_event.wait(sleep)


def main(configfile_path: str) -> int:

    #   prog default
    verbose: bool = False

    #   co2 driver default/init
    co2_driver: str = ""
    co2_sleep: int = 5
    
    userdata: PublisherUserdata = None

    # ========================================================
    #   Configuration file
    # ========================================================
    err, conf = DopUtils.parse_yaml_configuration(configfile_path)
    if err.isError():
        return err

    #   CO2
    co2_c = conf['co2']
    err, co2_conf = DopUtils.config_to_dict(co2_c['configuration'])


    #   mandatory args
    if 'driver' in co2_conf:
        co2_driver = co2_conf['driver']
    else:
        print('Missing arg: co2: driver')
        return 10

    if 'sleep' in co2_conf:
        co2_sleep = int(co2_conf['sleep'])

    #   PROG
    prog_c = conf['prog']
    err, prog_conf = DopUtils.config_to_dict(prog_c['configuration'])
    
    
    if 'v' in prog_conf:
        verbose = (prog_conf['v'] == '1')

    #   OUTPUT PROVIDER
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

    print(co2_conf)
    print(prog_conf)
    print(outputProvider_conf)


    if verbose:
        print(f'Broker host       : {host}')
        print(f'Broker port       : {port}')
        print(f'Bbroker topic     : {topic}') 

        print(f'CO2 driver        : {co2_driver}')
        print(f'CO2 sleep         : {co2_sleep}')


    # ====================================================================================
    # Main Functionality
    # ====================================================================================

    co2_p = Thread(target=thread_co2, args=(co2_conf, userdata, verbose))
    co2_p.start()
    time.sleep(1)
    
    co2_p.join()

    prov_err = output_provider.close()
    return prov_err

if __name__ == "__main__":
    
    global_stop_event = DopStopEvent()
    signalManagement()

    error: int = main(sys.argv[1])
    print(error)

