
from typing import Callable, Tuple

from common.python.error import DopError
from common.python.threads import DopStopEvent
from dvco_stub.abstract_pub_stack import AbstractPubStack

class PubStackStub(AbstractPubStack):
    def __init__(self):
        super().__init__()


    def init(self, pub_conf: dict):
        self._pub_conf = pub_conf


    def pump(self):
        return     
    

    def dopify(self, mess: bytes) -> Tuple[DopError, bytes]:
        return DopError(), mess
    