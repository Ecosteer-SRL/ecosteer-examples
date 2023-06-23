from _thread import allocate_lock
import time

class DopStopEvent:
    def __init__(self):
        self.i_stop_event = False
        self._lock = allocate_lock()

    def stop(self):
        with self._lock:
            self.i_stop_event = True
        
    def wait(self, timeout) -> bool:
        res = self._lock.acquire(True,timeout)
        if res:
            self._lock.release()
        return res
 

    def is_exiting(self) -> bool:
        
        with self._lock: 
            return self.i_stop_event
        