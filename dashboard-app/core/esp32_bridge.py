import threading
from typing import Optional, Callable

from common import FrameSize, LoggerInterface
from core.socket_handler import SocketHandler


class Esp32Bridge:

    FOV = 60

    def __init__(self, logger_class: Optional[LoggerInterface] = None):
        self.socket_handler = SocketHandler(logger_class=logger_class)
        self.logger_class = logger_class
        self.log_servo_commands = False
        self.test_mode = False
        self.auto_pan = False
        self.auto_tilt = False
        self.move_servo_callback: Optional[Callable[[], None]] = None
        self.servo_lock = threading.Lock()  # indicates that we are currently moving the servo
        self.queued_servo_duty: Optional[tuple[int, int]] = None
        self.frame_size = FrameSize.SVGA  # current frame size
        self.servo_degree = (90.0, 90.0)  # current servo position

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
        cmd_arg = frame_size.key
        response = self._send_command(f"FRAMESIZE {cmd_arg}")
        return response == "success"

    @staticmethod
    def _slow_panning(delta_degree: float) -> float:
        abs_degree = abs(delta_degree)
        if abs_degree > 10:
            abs_degree = 3
        elif abs_degree > 3:
            abs_degree = 1
        return abs_degree if delta_degree > 0 else abs_degree * -1

    def move_by_pixel(self, x: int, y: int) -> bool:
        if x == 0 and y == 0:
            return False
        pan_degree = tilt_degree = None
        if self.auto_pan is True:
            pan_delta_degree = (x / self.frame_size.width) * self.FOV
            pan_delta_degree = self._slow_panning(pan_delta_degree)   # TODO: a temporary solution
            pan_degree = self.servo_degree[0] - pan_delta_degree
        if self.auto_tilt is True:
            tilt_delta_degree = (y / self.frame_size.height) * self.FOV
            tilt_delta_degree = self._slow_panning(tilt_delta_degree)  # TODO: a temporary solution
            tilt_degree = self.servo_degree[1] - tilt_delta_degree
        return self.move_servo(pan_degree, tilt_degree)

    @staticmethod
    def _normalize_degree(degree: Optional[float]) -> Optional[float]:
        if degree is not None:
            degree = round(degree, 2)
            if degree < 0:
                degree = 0.0
            elif degree > 180:
                degree = 180.0
        return degree

    def move_servo(self, pan_degree: Optional[float], tilt_degree: Optional[float]) -> bool:
        pan_degree = self._normalize_degree(pan_degree)
        tilt_degree = self._normalize_degree(tilt_degree)
        if pan_degree is None and tilt_degree is None:
            return False
        if pan_degree is None:
            pan_degree = self.servo_degree[0] if self.queued_servo_duty is None else self.queued_servo_duty[0]
        if tilt_degree is None:
            tilt_degree = self.servo_degree[1] if self.queued_servo_duty is None else self.queued_servo_duty[1]
        servo_lock_acquired = self.servo_lock.acquire(blocking=False)
        if servo_lock_acquired is not True:
            self.queued_servo_duty = (pan_degree, tilt_degree)  # queue up the pan & tilt command
            return False
        while True:
            response = self._send_command(f"MOVE {pan_degree} {tilt_degree}")
            if response != "success":
                self.servo_lock.release()
                return False
            self.servo_degree = (pan_degree, tilt_degree)
            if self.move_servo_callback is not None:
                self.move_servo_callback()
            if self.queued_servo_duty is None:
                self.servo_lock.release()
                return True
            pan_degree, tilt_degree = self.queued_servo_duty
            self.queued_servo_duty = None
