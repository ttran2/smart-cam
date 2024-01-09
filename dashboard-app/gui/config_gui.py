import flet as ft

from common import FrameSize
from logic import VideoHandler


class ConfigGui(ft.UserControl):

    def __init__(self, video_handler: VideoHandler):
        super().__init__()
        self.video_handler = video_handler
        self.esp32_bridge = self.video_handler.esp32_bridge
        self.esp32_bridge.move_servo_callback = self.update_slider

        self.ip_textfield = ft.TextField(label="IP Address", prefix_text="https:// ", suffix_text="/camera",
                                         value="192.168.4.1", on_submit=self.submit_ip_address)
        self.connect_button = ft.ElevatedButton("connect", icon=ft.icons.VIDEOCAM_OUTLINED,
                                                on_click=self.submit_ip_address)
        self.flash_switch = ft.Switch(label="camera flash", value=False, on_change=self.toggle_flash)
        self.resolution_dropdown = ft.Dropdown(
            width=150,
            height=50,
            label="Resolution",
            options=[ft.dropdown.Option(frame_size.name) for frame_size in FrameSize],
            on_change=self.select_resolution,
        )
        self.cam_config_card = ft.Card(
            scale=2,
            opacity=0,
            animate_scale=True,
            animate_opacity=True,
            width=500,
            elevation=30,
            content=ft.Container(
                bgcolor=ft.colors.WHITE24,
                padding=30,
                border_radius=ft.border_radius.all(20),
                content=ft.Column([
                    ft.Text("ESP32 Cam Controls", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        controls=[self.flash_switch, self.resolution_dropdown]
                    )
                ]),
            )
        )
        self.auto_pan_switch = ft.Switch(label="auto-panning", value=False, on_change=self.toggle_auto_pan)
        self.auto_tilt_switch = ft.Switch(label="auto-tilting", value=False, on_change=self.toggle_auto_tilt)
        pan_value, tilt_value = self.esp32_bridge.servo_degree
        self.pan_slider = ft.Slider(min=0, max=180, divisions=180, label="{value}", value=pan_value,
                                    on_change=self.pan_servo)
        self.tilt_slider = ft.Slider(min=0, max=180, divisions=180, label="{value}", value=tilt_value,
                                     on_change=self.tilt_servo)
        self.servo_config_card = ft.Card(
            scale=2,
            opacity=0,
            animate_scale=True,
            animate_opacity=True,
            width=500,
            elevation=30,
            content=ft.Container(
                bgcolor=ft.colors.WHITE24,
                padding=30,
                border_radius=ft.border_radius.all(20),
                content=ft.Column([
                    ft.Text("Servo Controls", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        controls=[self.auto_pan_switch, self.auto_tilt_switch]
                    ),
                    ft.Text("Manual Panning", size=15, weight=ft.FontWeight.NORMAL),
                    self.pan_slider,
                    ft.Text("Manual Tilting", size=15, weight=ft.FontWeight.NORMAL),
                    self.tilt_slider
                ]),
            )
        )
        self.error_dialog = None

    def _close_error_dialog(self, event: ft.ControlEvent):
        self.error_dialog.open = False
        self.page.update()

    def _error_popup(self, title: str, message: str):
        self.error_dialog = ft.AlertDialog(
            title=ft.Row([ft.Icon(name=ft.icons.ERROR), ft.Text(title)]),
            content=ft.Text(message),
            actions_alignment=ft.MainAxisAlignment.END,
            actions=[ft.TextButton("Ok", on_click=self._close_error_dialog)]
        )
        self.page.dialog = self.error_dialog
        self.page.dialog.open = True
        self.page.update()

    def submit_ip_address(self, event: ft.ControlEvent):
        ip_address = self.ip_textfield.value.strip().lower()
        if ip_address == "":
            self._error_popup(
                title="No IP address provided",
                message="Please provide the IP address of the SMART Cam device."
            )
            return
        self.connect_button.disabled = self.ip_textfield.disabled = True
        connection_established = self.video_handler.set_video_input(source=ip_address)
        self.connect_button.disabled = self.ip_textfield.disabled = False
        if connection_established is False:
            self._error_popup(
                title="Connection Failed",
                message="No SMART Cam device was detected on the provided IP address!\n"
                        "Make sure you are connected to the SMART Cam Wi-Fi."
            )
            return
        response = self.esp32_bridge.connect(ip_address=ip_address)
        if response is False:
            self._error_popup(
                title="Communication Failed",
                message="Failed to establish a communication channel with the SMART Cam device!\n"
                        "Make sure the SMART Cam firmware is up-to-date."
            )
            return
        self.resolution_dropdown.value = self.esp32_bridge.frame_size = self.video_handler.determine_frame_size()
        self.cam_config_card.scale = self.cam_config_card.opacity = 1
        self.servo_config_card.scale = self.servo_config_card.opacity = 1
        self.update()

    def update_slider(self):
        pan_value, tilt_value = self.esp32_bridge.servo_degree
        if self.pan_slider.disabled is True:
            self.pan_slider.value = pan_value
            self.pan_slider.update()
        if self.tilt_slider.disabled is True:
            self.tilt_slider.value = tilt_value
            self.tilt_slider.update()

    def toggle_flash(self, event: ft.ControlEvent):
        self.esp32_bridge.set_flash(state=self.flash_switch.value)

    def select_resolution(self, event: ft.ControlEvent):
        frame_size = FrameSize[self.resolution_dropdown.value]
        self.esp32_bridge.set_frame_size(frame_size=frame_size)
        self.video_handler.set_frame_size(frame_size=frame_size)

    def toggle_auto_pan(self, event: ft.ControlEvent):
        if self.pan_slider.disabled != self.auto_pan_switch.value:
            self.pan_slider.disabled = self.auto_pan_switch.value
            self.update()
        self.esp32_bridge.auto_pan = self.auto_pan_switch.value

    def toggle_auto_tilt(self, event: ft.ControlEvent):
        if self.tilt_slider.disabled != self.auto_tilt_switch.value:
            self.tilt_slider.disabled = self.auto_tilt_switch.value
            self.update()
        self.esp32_bridge.auto_tilt = self.auto_tilt_switch.value

    def pan_servo(self, event: ft.ControlEvent):
        self.esp32_bridge.move_servo(pan_degree=self.pan_slider.value, tilt_degree=None)

    def tilt_servo(self, event: ft.ControlEvent):
        self.esp32_bridge.move_servo(pan_degree=None, tilt_degree=self.tilt_slider.value)

    def build(self):
        return ft.Column([
            ft.Card(
                width=500,
                elevation=30,
                margin=ft.margin.only(top=20),
                content=ft.Container(
                    bgcolor=ft.colors.WHITE24,
                    padding=30,
                    border_radius=ft.border_radius.all(20),
                    content=ft.Column([
                        ft.Text("Camera Connection", size=20, weight=ft.FontWeight.BOLD),
                        ft.Row([self.ip_textfield, self.connect_button])
                    ]),
                )
            ),
            self.cam_config_card,
            self.servo_config_card
        ])
