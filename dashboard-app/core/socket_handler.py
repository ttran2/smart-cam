import queue
import threading
import time
from typing import Optional

import websocket

from common import LoggerInterface


class SocketHandler:

    def __init__(self, logger_class: Optional[LoggerInterface] = None, timeout: int = 5):
        self.logger_class = logger_class
        self.timeout = timeout
        self.ws: Optional[websocket.WebSocketApp] = None
        self.thread: Optional[threading.Thread] = None
        self.connection_established = False
        self.response_queue = queue.Queue()

    def connect(self, ip_address: str) -> bool:
        self.connection_established = False
        ws = websocket.WebSocketApp(
            url=f"ws://{ip_address}/",
            on_open=self.on_open,
            on_message=self.on_message,
            on_error=self.on_error,
            on_close=self.on_close
        )
        thread = threading.Thread(target=ws.run_forever)
        thread.daemon = True
        thread.start()
        time_remaining = self.timeout * 10
        while self.connection_established is False and time_remaining > 0:
            time.sleep(.1)
            time_remaining -= 1
        if self.connection_established is True:
            self.thread = thread
        else:
            thread.join()
        return self.connection_established

    def send_command(self, command: str) -> Optional[str]:
        self.response_queue.queue.clear()
        self.ws.send(command)
        try:
            response = self.response_queue.get(timeout=self.timeout)
            return response
        except queue.Empty:
            msg = f"Timeout ({self.timeout}s) waiting for response to the following command: {command}"
            print(msg)
            if self.logger_class is not None:
                self.logger_class.log(message=msg, fg_color="red")

    def on_open(self, ws: websocket.WebSocketApp):
        self.ws = ws
        self.connection_established = True
        msg = f"Established connection to {self.ws.url} successfully!"
        print(msg)
        if self.logger_class is not None:
            self.logger_class.log(message=msg, fg_color="green")

    def on_close(self, ws: websocket.WebSocketApp):
        self.ws = None
        self.connection_established = False
        msg = f"Connection to {ws.url} has been closed."
        print(msg)
        if self.logger_class is not None:
            self.logger_class.log(message=msg, fg_color="orange")

    def on_message(self, ws: websocket.WebSocketApp, message):
        print(f"Receive websocket message ({type(message)}): {message}")  # TODO: remove this debug print
        self.response_queue.put(message)

    def on_error(self, ws: websocket.WebSocketApp, exception: websocket.WebSocketException):
        msg = f"Websocket Error ({type(exception)}): {exception}"
        print(msg)
        if self.logger_class is not None:
            self.logger_class.log(message=msg, fg_color="red")
