#   ver:    1.0
#   date:   27/01/2023
#   author: georgiana-bud

"""
Minimalistic implementation of platform's errors
"""
from enum import Enum
import json

class LogSeverity(Enum):
        NONE = 0
        DEBUG = 5
        INFO = 4
        WARN = 3
        ERROR = 2
        CRITICAL = 1

class DopError:
    

    def __init__(self, code: int=0, msg: str=""):
        self._code: int = code         #   error code default value 0
        self._msg: str = msg           #   error message default empty string
        #   the recoverable flag can be set to False by, for example, a provider
        #   that wants to notify that, for instance, it has not been able to 
        #   reconnect after a session failure, etc.
        #   in order to flag the error as non recoverable, use method "rip" (rest in peace)
        self._recoverable: bool = True 

        self._logSeverity: LogSeverity = LogSeverity.DEBUG 

        self._perr: DopError = None
                                        

    @property 
    def code(self) -> int:
        return self._code

    @property
    def msg(self) -> str:
        return self._msg

    @property
    def perr(self):
        return self._perr 

    @perr.setter 
    def perr(self, perr):
        self._perr = perr


    def isError(self) -> bool:
        return (self._code != 0)

    def isRecoverable(self) -> bool:
        return (self._recoverable)

    def rip(self) -> bool:
        #   rest in peace
        #   call this method if yoou need to flag the error as non recoverable
        self._recoverable = False
        return self._recoverable

    def to_dict(self) -> dict:
        perr = '' if self._perr is None else self._perr.to_dict()
        return {'code':self._code, 'msg':self._msg, 'per': perr}

    def __repr__(self):
        perr = '' if self._perr is None else self._perr.to_dict()
        return json.dumps({'code':self._code, 'msg':self._msg, 'per':perr})
