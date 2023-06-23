

from threading import Event, Thread

class DopStopEvent:
    def __init__(self):
        self.i_stop_event = Event()
        self.i_stop_event.clear()

    def stop(self):
        self.i_stop_event.set()
        
    def wait(self, timeout) -> bool:
        return self.i_stop_event.wait(timeout)

    def is_exiting(self) -> bool:
        return self.i_stop_event.is_set()