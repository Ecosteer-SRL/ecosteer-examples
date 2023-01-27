#   ver:    1.0
#   date:   27/01/2023
#   author: georgiana-bud

import sys

from typing import Callable
from abc import ABC, abstractmethod



#   import from packages and modules within the ecosteer project
from common.python.error import DopError
from common.python.threads import DopStopEvent


class Provider(ABC):

    def __init__(self):
        """
        as the base class implements __init__, make sure to call super.__init__()
        from any derived class

        a i_stop_event attribute is initialized no matter what, so any call to is_exiting, etc.
        will be consistent even if no stop event is attached to the provider        
        """
        self.i_stop_event = DopStopEvent()
        self.i_last_error = DopError()

        #   callback function: on_data_fun(message_topic: str, message_payload: str, userdata)
        #   callback function: on_error_fun(err: DopError, userdata)
        self._on_data_fun: Callable = None
        self._on_error_fun: Callable = None
        self._userdata = None

    
    def attach_stop_event(self, stop_event: DopStopEvent):
        """
        attach a stop event to the provider

        the provider, by checking the status of the stop event, will know
        if the provider consumer (the main process) has notified an exit condition
        this is particularly useful if the provider implements retry loops that can be
        stopped by an exit notification
        """
        self.i_stop_event = stop_event

    def _on_error(self, err: DopError):
        """
        """
        self.set_lastError(err)
        if self._on_error_fun != None:
            self._on_error_fun(err, self._userdata)
        
    def _on_data(self, event_topic: str, event_msg: str):
        """
        this method has to be called by the inherited class to notify
        data availability
        """

        #   the incoming message will be propagated to the upper layers
        #   in str representation. it is responsibility of the upper layer
        #   to convert the "raw" str in any possible structure/object
        if self._on_data_fun != None:
            self._on_data_fun(event_topic, event_msg, self._userdata)

    
    def set_userdata(self,userdata):
        self._userdata = userdata

    def set_on_data_callback(self,fun_callback: Callable):
        """
        assign the user defined callback
        """
        self._on_data_fun = fun_callback

    def set_on_error_callback(self, fun_callback: Callable):
        """
        assign the user defined callback
        """
        self._on_error_fun = fun_callback


    @property
    def stopEvent(self) -> DopStopEvent:
        return self.i_stop_event

    @property
    def lastError(self) -> DopError:
        return self.i_last_error
    
    def set_lastError(self, err: DopError):
        self.i_last_error = err
        

    @abstractmethod
    def init(self, config: str) -> DopError:
        """
        parse the config file and set the variables used
        to configure and use the provider
        :param config: string
        """

    @abstractmethod
    def open(self) -> DopError:
        """
        Open the connection with a provider using the configs options
        """

    @abstractmethod
    def close(self) -> DopError:
        """
        Close the connection with the provider
        """

