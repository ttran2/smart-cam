import flet as ft

from logic import VideoHandler


class TrackerGui(ft.UserControl):

    def __init__(self, video_handler: VideoHandler):
        super().__init__()
        self.video_handler = video_handler
        self.cam_controller = self.video_handler.cam_controller

        self.model_dropdown = ft.Dropdown(
            width=150,
            height=50,
            label="YOLO Model",
            options=[ft.dropdown.Option(model_name) for model_name in self.video_handler.list_downloaded_models()],
            on_change=self.select_model,
        )
        self.tracking_switch = ft.Switch(label="tracking disabled", value=self.cam_controller.tracking_enabled,
                                         on_change=self.toggle_tracking)
        self.show_bounding_box_switch = ft.Switch(label="bounding box", value=self.video_handler.show_bounding_boxes,
                                                  on_change=self.toggle_bounding_box)
        self.show_target_center_switch = ft.Switch(label="target center", value=self.cam_controller.show_center,
                                                   on_change=self.toggle_target_center)
        self.show_arrows_switch = ft.Switch(label="arrows", value=self.cam_controller.show_arrows,
                                            on_change=self.toggle_arrows)
        self.show_boundaries_switch = ft.Switch(label="boundaries", value=self.cam_controller.show_boundaries,
                                                on_change=self.toggle_boundaries)
        self.boundary_slider = ft.Slider(width=600, label="{value}", value=self.cam_controller.boundary_offset,
                                         min=0, max=300, divisions=300, on_change=self.sliding_boundary)
        self.coyote_slider = ft.Slider(width=600, label="{value}", value=self.cam_controller.coyote_seconds,
                                       min=0, max=10, divisions=10, on_change=self.sliding_coyote)
        # TODO: add boundary and coyote RESET icon to reset the values to DEFAULT values

    def select_model(self, event: ft.ControlEvent):
        self.video_handler.set_model(model_name=self.model_dropdown.value)

    def toggle_tracking(self, event: ft.ControlEvent):
        self.cam_controller.tracking_enabled = self.tracking_switch.value
        self.tracking_switch.label = "tracking enabled" if self.tracking_switch.value is True else "tracking disabled"
        self.update()

    def toggle_bounding_box(self, event: ft.ControlEvent):
        self.video_handler.show_bounding_boxes = self.show_bounding_box_switch.value

    def toggle_target_center(self, event: ft.ControlEvent):
        self.cam_controller.show_center = self.show_target_center_switch.value

    def toggle_arrows(self, event: ft.ControlEvent):
        self.cam_controller.show_arrows = self.show_arrows_switch.value

    def toggle_boundaries(self, event: ft.ControlEvent):
        self.cam_controller.show_boundaries = self.show_boundaries_switch.value

    def sliding_boundary(self, event: ft.ControlEvent):
        self.cam_controller.resize_boundary(boundary_offset=self.boundary_slider.value)

    def sliding_coyote(self, event: ft.ControlEvent):
        self.cam_controller.coyote_seconds = self.coyote_slider.value

    def build(self):
        return ft.Card(
            width=500,
            elevation=30,
            margin=ft.margin.only(top=20),
            content=ft.Container(
                bgcolor=ft.colors.WHITE24,
                padding=30,
                border_radius=ft.border_radius.all(20),
                content=ft.Column([
                    ft.Text("Tracker Settings", size=20, weight=ft.FontWeight.BOLD),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        controls=[self.model_dropdown, self.tracking_switch]
                    ),
                    ft.Text("Heads-Up Display", size=15, weight=ft.FontWeight.NORMAL),
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_AROUND,
                        controls=[
                            ft.Column([self.show_bounding_box_switch, self.show_arrows_switch]),
                            ft.Column([self.show_target_center_switch, self.show_boundaries_switch])
                        ]
                    ),
                    ft.Text("Boundary Size", size=15, weight=ft.FontWeight.NORMAL),
                    self.boundary_slider,
                    ft.Text("Coyote Pause (in seconds)", size=15, weight=ft.FontWeight.NORMAL),
                    self.coyote_slider
                ]),
            )
        )
