#   ver:    1.0
#   date:   27/01/2023
#   author: georgiana-bud


import sys
#sys.path.append('...')

from abc import ABC, abstractmethod
from typing import Tuple, NewType

from common.python.error import DopError
from provider.python.provider import Provider

DopEvent = NewType('DopEvent', object)


class outputPresentationProvider(Provider):
    @abstractmethod
    def write(self, msg: str) -> DopError:
        pass

    @abstractmethod 
    def writeEvent(self, msg: DopEvent) -> DopError:
        pass