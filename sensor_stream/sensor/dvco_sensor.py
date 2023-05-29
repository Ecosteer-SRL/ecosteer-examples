#   ver:    1.1
#   date:   23/05/2023
#   author: georgiana-bud

#   Version 1.1 
#   Changed logic of callback method

import argparse
import datetime
import json
import os
import signal
import time
from threading import Event, Thread, Lock

from externals.CO2Meter import *
from common.python.utils import DopUtils
from common.python.error import DopError
from common.python.threads import DopStopEvent

from dvco_stub.pub_stack_stub import PubStackStub

#   usage: sensor.py -c configFile.yaml -p product.json

global_stop_event: DopStopEvent
global_print_lock: Lock


def get_args(argl = None):
    
    parser = argparse.ArgumentParser(description="Sensor stream program, modified with the \
                                addition of the DVCO pub stack stub. ")
    parser.add_argument("-c", "--config",
        help = "The configuration file for the main program.", 
        required = True)
    
    parser.add_argument("-p", "--product",
        help = "The product configuration file for the DVCO stack.")
    
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

    


def publish_callback(payload: str, userdata) -> DopError:
    print(payload)
    return publish(payload, userdata)



def thread_dvco(configuration: dict, pub_stack, verbose):
    loop_interval = configuration['loop_interval']
    
    while True:   
        if global_stop_event.is_exiting():
            break 
        
        pub_stack.pump()

        time.sleep(loop_interval/1000)
        

    

def thread_co2(configuration: dict, pub_stack, userdata, verbose):
    run: int = int(configuration['run'])

    if run!=1:
        return

    co2_driver = configuration['driver']
    sleep: int     = int(configuration['sleep'])

    sensor = CO2Meter(co2_driver)

    counter:int = 0

    while True:   
        if global_stop_event.is_exiting():
            break

        d = sensor.get_data()
        d['now'] = str(datetime.datetime.now())
        d['payload_number'] = f"{counter}"
        counter = counter +1
        
        #   dopify
        payload: str = str(d)
        
        if verbose:
            msg = {"hrMsg":"TRACE unencrypted payload",
                "payload": payload
            }   
            synced_print(json.dumps(msg))


        res = pub_stack.dopify(payload.encode("UTF-8"))
        err = res[0]
        dopified_mess = res[1] 
        #synced_print(dopified_mess.decode("UTF-8"))

        global_stop_event.wait(sleep)


def main(args) -> DopError:

    #   Parse arguments
    config_file = args.config 
    product_file = args.product 


    if not os.path.exists(config_file):
        return DopError(101,"Configuration file does not exist")

    if not os.path.exists(product_file):
        return DopError(101,"Configuration file does not exist")  

    #   prog default
    verbose: bool = False

    #   co2 driver default/init
    co2_driver: str = ""
    co2_sleep: int = 5
    
    userdata: PublisherUserdata = None

    # ========================================================
    #   Main Configuration file
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

    # ========================================================
    #   Publisher Configuration file
    # ========================================================

    dvco_conf = {}
    with open(product_file) as conf:
        try:
            dvco_conf = json.loads(conf.read())
        except Exception: 
            return DopError(2, "Error in loading JSON configuration file.")
    
    if 'loop_interval' not in dvco_conf:
        return DopError(11,"Missing product arg: loop_interval")


    # Userdata 
    userdata = PublisherUserdata()
    userdata.output_provider = output_provider

    #print(co2_conf)
    #print(prog_conf)
    #print(outputProvider_conf)


    if verbose:
        print(f'Broker host       : {host}')
        print(f'Broker port       : {port}')
        print(f'Bbroker topic     : {topic}') 

        print(f'CO2 driver        : {co2_driver}')
        print(f'CO2 sleep         : {co2_sleep}')

    

    # Pub stack
    pub_stack = PubStackStub()
    pub_stack.init(dvco_conf)
    pub_stack.attach_stop_event(global_stop_event)
    pub_stack.set_pub_userdata(userdata)
    pub_stack.set_pub_callback(publish_callback)

    # ====================================================================================
    # Main Program
    # ====================================================================================

    dvco_t = Thread(target = thread_dvco, args=(dvco_conf, pub_stack, verbose))
    dvco_t.start()

    co2_t = Thread(target=thread_co2, args=(co2_conf, pub_stack, userdata, verbose))
    co2_t.start()

    time.sleep(1)
    
    dvco_t.join()
    co2_t.join()

    prov_err = output_provider.close()
    return prov_err

if __name__ == "__main__":
    
    global_stop_event = DopStopEvent()
    global_print_lock = Lock()
    signalManagement()

    error: DopError = main(get_args())
    print(error)

