import datetime
from typing import Optional

import flet as ft

from common import LoggerInterface
from logic import VideoHandler


class LoggingGui(ft.UserControl, LoggerInterface):

    def __init__(self, video_handler: VideoHandler):
        super().__init__()
        self.video_handler = video_handler
        self.esp32_bridge = self.video_handler.esp32_bridge
        self.esp32_bridge.socket_handler.logger_class = self  # always log websocket connections
        self.log_length_dropdown = ft.Dropdown(
            width=100,
            height=50,
            label="Length",
            options=[ft.dropdown.Option(i) for i in (50, 100, 200, 500)],
            value="50",
            on_change=self.select_log_length,
        )
        self.tracking_log_switch = ft.Switch(label="tracking", value=False, on_change=self.toggle_tracking_log)
        self.cam_log_switch = ft.Switch(label="esp32 cam", value=False, on_change=self.toggle_cam_log)
        self.servo_log_switch = ft.Switch(label="servos", value=False, on_change=self.toggle_servo_log)
        self.log_list_view = ft.ListView(expand=True, auto_scroll=True, spacing=10, padding=20)

    def log(self, message: str, fg_color: Optional[str] = None, bg_color: Optional[str] = None) -> None:
        timestamp = datetime.datetime.now().strftime("%H:%M:%S")
        print(message)  # TODO: remove this debug printing
        self.log_list_view.controls.append(
            ft.Text(
                value=f"[{timestamp}] ", color=fg_color, bgcolor=bg_color, weight=ft.FontWeight.BOLD,
                spans=[
                    ft.TextSpan(message, ft.TextStyle(weight=ft.FontWeight.NORMAL))
                ]
            )
        )
        self._limit_log()

    def _limit_log(self):
        count = len(self.log_list_view.controls)
        length = int(self.log_length_dropdown.value)
        if count > length:
            remove = count - length
            self.log_list_view.controls = self.log_list_view.controls[remove:]
        self.log_list_view.update()

    def select_log_length(self, event: ft.ControlEvent):
        self._limit_log()

    def toggle_tracking_log(self, event: ft.ControlEvent):
        if self.video_handler.logger_class is None:
            self.video_handler.logger_class = self
            self.video_handler.cam_controller.logger_class = self
        else:
            self.video_handler.logger_class = None
            self.video_handler.cam_controller.logger_class = self

    def toggle_cam_log(self, event: ft.ControlEvent):
        if self.esp32_bridge.logger_class is None:
            self.esp32_bridge.logger_class = self
            self.servo_log_switch.value = self.esp32_bridge.log_servo_commands
            self.servo_log_switch.disabled = False
        else:
            self.esp32_bridge.logger_class = None
            self.servo_log_switch.value = False
            self.servo_log_switch.disabled = True
        self.update()

    def toggle_servo_log(self, event: ft.ControlEvent):
        self.esp32_bridge.log_servo_commands = self.servo_log_switch.value

    def build(self):
        return ft.Card(
            width=500,
            elevation=30,
            margin=ft.margin.only(top=20, bottom=70),
            content=ft.Container(
                bgcolor=ft.colors.WHITE24,
                padding=30,
                border_radius=ft.border_radius.all(20),
                content=ft.Column([
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Debug Logging", size=20, weight=ft.FontWeight.BOLD),
                            self.log_length_dropdown
                        ]
                    ),
                    ft.Text("Log Filters", size=15, weight=ft.FontWeight.NORMAL),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        controls=[self.tracking_log_switch, self.cam_log_switch, self.servo_log_switch]
                    ),
                    ft.Text("Logs", size=15, weight=ft.FontWeight.NORMAL),
                    ft.Container(
                        expand=True,
                        bgcolor=ft.colors.WHITE30,
                        border_radius=ft.border_radius.all(20),
                        content=self.log_list_view
                    )
                ]),
            )
        )
