#   ver:    1.0
#   date:   17/05/2023
#   author: georgiana-bud


import json
import sys
#sys.path.append("...")

import os
import hashlib
import paho.mqtt.client as mqtt
import time
import threading
from threading import Event
import uuid


from inspect import currentframe, getframeinfo
import traceback

from common.python.error import DopError
from common.python.utils import DopUtils 
from common.python.threads import DopStopEvent

class MqttClient: 
    
    def __init__(self):
        self._output_client = None
        #self._client_id: str = "hjkhjkhjkhjkhjk"
        self._client_session: bool = False
        self._protocol = mqtt.MQTTv311
        self._transport: str = "tcp"                  #   could be websocket (if set to websocket, the logic would be slightly different)
        self._port: int = 1883
        self._keepalive: int = 10
        #self._bind_address: str = ""
        self._qos: int = 1
        self._configured: bool = False
        self._timeout: int = 20
        self._last_mid: int = 0
        self._max_retries: int = 5
        self._retries_count: int = 0

        
        self.i_stop_event = DopStopEvent()
        self._connection_event: Event = Event()
        self._connection_event.clear()
        self._published_event: Event = Event()

        super().__init__()


    def init(self,connstring: str) -> DopError:
       
        #   connstring example
        #   host=10.170.30.66;port=1883;topic=test_topic;retrycount=10;keepalive=60;qos=1;timeout=10;prefix=grz_;
        #   h=10.170.30.66;p=1883;t=test_topic;rc=10;ka=60;q=1;tout=10;prf=grz_;
        tupleConfig = DopUtils.config_to_dict(connstring)
        if tupleConfig[0].isError():
            return tupleConfig[0]

        #   mandatory parameters
        has_host = False
        has_topic = False
        
        d_config: dict = tupleConfig[1]
        has_host, self._host = DopUtils.config_get_string(d_config, ['host','h'], None)
        has_topic, self.topic = DopUtils.config_get_string(d_config, ['topic','t'], None)

        wfc, self._bind_address = DopUtils.config_get_string(d_config,['bindaddress','ba'],"")
        wfc, self._port = DopUtils.config_get_int(d_config,['port','p'],1883)
        wfc, self._max_retries = DopUtils.config_get_int(d_config,['retrycount','rc'],10)
        wfc, self._keepalive = DopUtils.config_get_int(d_config,['keepalive','ka'],60)
        wfc, self._qos = DopUtils.config_get_int(d_config,['qos','q'],1)
        wfc, self._timeout = DopUtils.config_get_int(d_config,['timeout','tout'],20)

            
        wfc, prefix = DopUtils.config_get_string(d_config, ['prefix','prf'], None)

        self._client_id = self.generate_client_id(prefix)
            
        if (has_host and has_topic) == False:
            err = DopError(1,"Configuration missing mandatory parameter(s).")
            return err

        if (self._qos < 0) or (self._qos>2):
            self._qos = 1
            print("invalid qos, using default")

        if self._timeout < 0:
            self._timeout = 20
            print("invalid timeout, using default")

        self._configured = True 

        print("provider configured")  
        return DopError()

    

    @property
    def stopEvent(self) -> DopStopEvent:
        return self.i_stop_event

    
    def attach_stop_event(self, stop_event: DopStopEvent):
        """
        attach a stop event to the provider

        the provider, by checking the status of the stop event, will know
        if the provider consumer (the main process) has notified an exit condition
        this is particularly useful if the provider implements retry loops that can be
        stopped by an exit notification
        """
        self.i_stop_event = stop_event

    #       callbacks
    def on_connect(self, client, userdata, flags, rc):
        print(f"connected with result code {rc}")
        if rc != 0:
            #   failure connecting
            err = DopError(100,"Could not connect to the broker.")
            print(err)
            if self.stopEvent.is_exiting() == False:
                if self._max_retries > self._retries_count:
                    self._retries_count += 1
                    self.open()
            return

        #   signal connection
        self._connection_event.set()
            

    def on_disconnect(self, client, userdata, rc):
        self._connection_event.clear()
        if rc != 0:
            err = DopError(103,"Unexpected disconnection.")
            print(err)

        if self.stopEvent.is_exiting() == False:
            #   no higher-level exit has been signalled
            #   ==> try to reconnect
            self.open()

    @staticmethod
    def wait_for_event_status(timeout: int, event: Event, status: bool) -> bool:
        """
        waits on event for status
        if timeout expires, the method returns False, True otherwise
        NOTE:       this static method could be moved to a shared/common module
        """
        elapsed: int = 0
        while event.is_set() != status:
            time.sleep(1)
            elapsed += 1
            if elapsed >= timeout:
                return False
        return True


    @staticmethod
    def generate_client_id(prefix: str) -> str:
        """
            this has to generate a unique id for the host.process.thread
            as on the same host there might be several processes using the provider
            and within the same process there might be several thread using the provider
        """
        host_id: int = uuid.getnode()
        proc_id: int = os.getpid()
        thrd_id: int = threading.current_thread().ident

        #   do not show your MAC
        if prefix == None:
            strkey: str = str(host_id) + str(proc_id) + str(thrd_id)
        else:
            strkey: str = prefix + str(host_id) + str(proc_id) + str(thrd_id)

        client_id: str = hashlib.md5(strkey.encode()).hexdigest()
        return client_id

    def on_publish(self, client, userdata, result):  # create function for callback
        pass

    def _open(self) -> DopError:
        try: 
            self.close()
            self._output_client.connect_async(self._host, port=self._port,
                    keepalive=self._keepalive, bind_address=self._bind_address)
            self._output_client.loop_start()
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()

            return DopError(99,"An exception occurred while connecting to the broker.")
        
        if self.wait_for_event_status(self._timeout, self._connection_event, True) == False:
            err: DopError = DopError(101,"Cannot connect to broker: timeout expired.")
            print(err)
            return err

        return DopError()       

    def open(self) -> DopError:
        if not self._configured:
            return DopError(2, "Provider cannot open: it is not yet configured.")
            
        self._output_client = mqtt.Client()
        self._output_client.on_publish = self.on_publish
        self._output_client.on_connect = self.on_connect
        self._output_client.on_disconnect = self.on_disconnect

        err: DopError = DopError()
        while self.stopEvent.is_exiting() == False:    
            print(f"Opening output mqtt provider retry count {self._retries_count}")
            err = self._open()
            if err.isError() == False:
                break

            if self._max_retries < self._retries_count:
                #   maximum number of retries has been exceeded
                err.rip()   #   this has tp be considered a non recoverable error
                return err
            self._retries_count += 1

        self._retries_count = 0   
        err = DopError(0,"output mqtt provider opened")
        return DopError()


    def close(self) -> DopError:
        if self._connection_event.is_set():
            self._output_client.disconnect()
            
            #wait for disconnection
            self.wait_for_event_status(self._timeout, self._connection_event, False)
            self._output_client.loop_stop()
        err = DopError(0,"output mqtt provider closed")
        
        return err

    def write(self, msg: str) -> DopError:
        try:
            err, res = self._output_client.publish(
                self._topic, msg, qos = self._qos)

            if err != 0:
                return DopError(201, "An error occurred while publishing a message.")
        except Exception as e:
            print(f"{int(time.time())} | {getframeinfo(currentframe()).filename} | "\
                    f"{getframeinfo(currentframe()).lineno} | {type(e)} | {traceback.format_exc()}", file = sys.stderr)
            sys.stderr.flush()

            return DopError(202, "An exception occurred while publishing a message.")
		
        return DopError(0, "Event published")
   