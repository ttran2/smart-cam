from typing import Optional

from common import FrameSize, LoggerInterface
from core.socket_handler import SocketHandler


class Esp32Bridge:

    def __init__(self, logger_class: Optional[LoggerInterface] = None):
        self.socket_handler = SocketHandler(logger_class=logger_class)
        self.logger_class = logger_class
        self.log_servo_commands = False
        self.test_mode = False

    def connect(self, ip_address: str) -> bool:
        if ip_address == "0":
            self.test_mode = True
            return True
        response = self.socket_handler.connect(ip_address=ip_address)
        if response is True:
            response = self.ping()
        return response

    def _mock_interaction(self, command: str) -> str:
        if command == "PING":
            return "PONG"
        return "success"

    def _send_command(self, command: str, is_servo_command: bool = False) -> Optional[str]:
        should_log = self.logger_class is not None and (is_servo_command is False or self.log_servo_commands is True)
        if should_log is True:
            self.logger_class.log(message=f"Send Command: {command}")
        if self.test_mode is False:
            response = self.socket_handler.send_command(command=command)
        else:
            response = self._mock_interaction(command=command)
        if should_log is True:
            self.logger_class.log(message=f"    response: {response}")
        return response

    def ping(self) -> bool:
        response = self._send_command("PING")
        return response == "PONG"

    def set_flash(self, state: bool) -> bool:
        cmd_arg = "on" if state is True else "off"
        response = self._send_command(f"FLASH {cmd_arg}")
        return response == "success"

    def set_frame_size(self, frame_size: FrameSize) -> bool:
        cmd_arg = frame_size.name.lower()
        response = self._send_command(f"FRAMESIZE {cmd_arg}")
        return response == "success"

    def move_by_pixel(self, x: int, y: int) -> bool:
        if x == 0 and y == 0:
            return
        # self._send_command(f"MOVE {} {}")
        # TODO: calculate pixel distance to servo duty
        # TODO: send servo duty with move_servo method

    def move_servo(self, pan_servo_duty: int, tilt_servo_duty: int) -> bool:
        if pan_servo_duty == 0 and tilt_servo_duty == 0:
            return
        # TODO: send MOVE command to move the servo
