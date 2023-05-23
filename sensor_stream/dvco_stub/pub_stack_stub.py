
from typing import Callable, Tuple
from threading import Lock 


from common.python.error import DopError
from common.python.threads import DopStopEvent
from dvco_stub.abstract_pub_stack import AbstractPubStack

class PubStackStub(AbstractPubStack):
    def __init__(self):
        super().__init__()
        self._callback_lock: Lock = Lock()


    def init(self, pub_conf: dict):
        self._pub_conf = pub_conf


    def pump(self):
        return     
    

    def dopify(self, mess: bytes) -> Tuple[DopError, bytes]:
        self._on_dopified_message(mess.decode("UTF-8"))
        return DopError(), mess

    def _on_dopified_message(self, mess):
        
        if self._pub_callback is not None:
            with self._callback_lock: 
                self._pub_callback(mess, self._pub_userdata)

    