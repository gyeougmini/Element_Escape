from pico2d import *

# 버튼 시트는 가로로 8프레임: 0~7로 갈수록 네온이 깜빡이며 켜짐
BUTTON_FRAMES = 8
NORMAL_FRAME = 3   # 마우스가 올라가지 않았을 때 보여줄 프레임 (흐리게 켜진 상태)
HOVER_FPS = 24     # 마우스를 올렸을 때 0~7 프레임을 재생하는 속도, 마지막 프레임에서 멈춤


class Button:
    def __init__(self, image_path, frame_width, frame_height, x, y, on_click):
        self.image = load_image(image_path)
        self.frame_width, self.frame_height = frame_width, frame_height
        self.x, self.y = x, y
        self.on_click = on_click
        self.hovered = False
        self.hover_time = 0.0

    def contains(self, x, y):
        return (abs(x - self.x) <= self.frame_width / 2 and
                abs(y - self.y) <= self.frame_height / 2)

    def handle_event(self, event):
        if event.type not in (SDL_MOUSEMOTION, SDL_MOUSEBUTTONDOWN):
            return
        # SDL 마우스 좌표는 위에서부터이므로 pico2d 좌표로 뒤집음
        x, y = event.x, get_canvas_height() - 1 - event.y
        if event.type == SDL_MOUSEMOTION:
            hovered = self.contains(x, y)
            if hovered and not self.hovered:
                self.hover_time = 0.0
            self.hovered = hovered
        elif event.button == SDL_BUTTON_LEFT and self.contains(x, y):
            self.on_click()

    def update(self, frame_time):
        if self.hovered:
            self.hover_time += frame_time

    def draw(self):
        if self.hovered:
            frame = min(int(self.hover_time * HOVER_FPS), BUTTON_FRAMES - 1)
        else:
            frame = NORMAL_FRAME
        self.image.clip_draw(frame * self.frame_width, 0, self.frame_width, self.frame_height,
                             self.x, self.y)
