
from abc import ABC, abstractmethod
from typing import Callable, Tuple

from common.python.error import DopError
from common.python.threads import DopStopEvent

class AbstractPubStack(ABC):

    def __init__(self):
        self._pub_conf = None
        self._stop_event: DopStopEvent = None

        # Callback 

        self._pub_callback: Callable = None #pub_callback needs to take as parameters: payload, userdata
        self._pub_userdata = None
    
    @abstractmethod 
    def init(self, pub_conf: dict):
        pass 

    
    @abstractmethod
    def pump(self):
        pass     
    
    @abstractmethod
    def dopify(self, mess: bytes) -> Tuple[DopError, bytes]:
        pass
    

    def set_pub_callback(self, pub_callback: Callable):    
        """ Set the callback for the publisher. """
        self._pub_callback = pub_callback
    

    def set_pub_userdata(self, pub_userdata):
        """ Set the userdata for the publisher. """
        self._pub_userdata = pub_userdata

    
    def attach_stop_event(self, stop_event: DopStopEvent):
        """ Attach a stop event to the pub stack, to exit loop in case of a user interrupt. """
        self._stop_event = stop_event
