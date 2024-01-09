import time

import flet as ft

from logic import VideoHandler


class CameraGui(ft.UserControl):

    def __init__(self, video_handler: VideoHandler):
        super().__init__()
        self.video_handler = video_handler
        self.last_frame_time = 0

        self.theme_button = ft.IconButton(on_click=self.toggle_theme)
        self.camera_feed_image = ft.Image(
            border_radius=ft.border_radius.all(20),
            visible=False
        )
        self.no_cam_container = ft.Container(
            width=800,
            height=600,
            bgcolor=ft.colors.WHITE24,
            padding=10,
            border_radius=ft.border_radius.all(20),
            alignment=ft.alignment.center,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.CENTER,
                controls=[
                    ft.ProgressRing(width=30, height=30, stroke_width=5),
                    ft.Text("  no camera connection...", style=ft.TextThemeStyle.HEADLINE_SMALL),
                ]
            )
        )
        self.fps_value_label = ft.Text("n/a", size=15, weight=ft.FontWeight.NORMAL)

    def did_mount(self):
        """ Load update_timer() when FLET run """
        self.update_timer()

    def update_timer(self):
        while True:
            base64_frame = self.video_handler.process_frame()

            if base64_frame is None:
                if self.camera_feed_image.visible is True:
                    self.camera_feed_image.visible = False
                    self.fps_value_label.value = "n/a"
                    self.update()
                time.sleep(.1)
                continue

            if self.camera_feed_image.visible is False:
                self.camera_feed_image.visible = True
                frame_width, frame_height = self.video_handler.get_frame_size()
                self.no_cam_container.width = frame_width
                self.no_cam_container.height = frame_height

            self.update_fps()
            self.camera_feed_image.src_base64 = base64_frame
            self.no_cam_container.width, self.no_cam_container.height = self.video_handler.get_frame_size()
            self.update()

    def initialize_theme(self, page: ft.Page):
        self.page = page
        if self.page.theme_mode is None or self.page.theme_mode.SYSTEM:
            self.page.theme_mode = self.page.platform_brightness
        self._update_theme()

    def _update_theme(self):
        if self.page.theme_mode == ft.ThemeMode.LIGHT:
            self.theme_button.icon = ft.icons.LIGHT_MODE
            self.theme_button.tooltip = "Switch to DARK Mode"
        else:
            self.theme_button.icon = ft.icons.DARK_MODE
            self.theme_button.tooltip = "Switch to LIGHT Mode"
        self.page.update()

    def toggle_theme(self, event: ft.ControlEvent):
        self.page.theme_mode = ft.ThemeMode.DARK if self.page.theme_mode == ft.ThemeMode.LIGHT else ft.ThemeMode.LIGHT
        self._update_theme()
        self.theme_button.update()

    def build(self):
        return ft.Column([
            ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                controls=[
                    ft.Text("SMART Cam", size=30, weight=ft.FontWeight.BOLD),
                    self.theme_button
                ]
            ),
            ft.Column([
                ft.Stack([self.no_cam_container, self.camera_feed_image]),
                ft.Row([
                    ft.Text("FPS : ", size=15, weight=ft.FontWeight.BOLD),
                    self.fps_value_label
                ])
            ]),
        ])

    def update_fps(self):
        new_frame_time = time.time()
        fps = 1 / (new_frame_time - self.last_frame_time)
        self.fps_value_label.value = f"{fps:.2f}"
        self.last_frame_time = new_frame_time
