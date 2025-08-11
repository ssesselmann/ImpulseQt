# status_bar_handler.py
import logging

class StatusBarHandler(logging.Handler):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback  # expects (msg: str, level: int)

    def emit(self, record):
        try:
            msg = self.format(record)
            self.callback(msg, record.levelno)   # <-- pass level too
        except Exception:
            self.handleError(record)
