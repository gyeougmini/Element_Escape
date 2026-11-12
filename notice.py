import ctypes

from pico2d import *
from sdl2.sdlttf import TTF_SizeUTF8

from dialogue import FONT_PATH

NOTICE_IMAGE = 'sprite_sheet/sprite_sheet_dialugue/notice_slide_box.png'
FRAME_WIDTH, FRAME_HEIGHT = 512, 128  # 8프레임: 위에서 내려오며 펼쳐지고 7번 프레임에서 다 나옴
FRAMES = 8
SLIDE_FPS = 24
TEXT_CENTER_Y = 60   # 다 펼쳐진 상자 안에서 글자 중심의 y (프레임 위쪽 기준 픽셀)
FONT_SIZE = 28
TEXT_COLOR = (235, 235, 235)


class Notice:
    """화면 위쪽 가운데에 내려왔다가, hold_time 동안 문구를 보여주고, 다시 올라가는 안내창"""
    font = None

    def __init__(self, text, hold_time, delay=0.0):
        if Notice.font is None:
            Notice.font = load_font(FONT_PATH, FONT_SIZE)
        self.image = load_image(NOTICE_IMAGE)
        self.text = text
        self.hold_time = hold_time
        self.delay = delay  # 나타나기 전 기다리는 시간
        self.time = 0.0
        self.slide_time = (FRAMES - 1) / SLIDE_FPS

    def is_done(self):
        return self.time >= self.delay + self.slide_time * 2 + self.hold_time

    def update(self, frame_time):
        self.time += frame_time

    def current_frame(self):
        # 등장 전이거나 끝났으면 None
        t = self.time - self.delay
        if t < 0 or self.is_done():
            return None
        if t < self.slide_time:                        # 내려오는 중
            return int(t * SLIDE_FPS)
        t -= self.slide_time
        if t < self.hold_time:                         # 다 펼쳐진 상태
            return FRAMES - 1
        t -= self.hold_time
        return FRAMES - 1 - int(t * SLIDE_FPS)         # 올라가는 중

    def draw(self):
        frame = self.current_frame()
        if frame is None:
            return
        x = get_canvas_width() // 2
        top = get_canvas_height()
        self.image.clip_draw(frame * FRAME_WIDTH, 0, FRAME_WIDTH, FRAME_HEIGHT,
                             x, top - FRAME_HEIGHT / 2)
        if frame == FRAMES - 1:
            # pico2d의 font.draw는 x가 글자 왼쪽 끝이므로 글자 폭을 재서 가운데 정렬
            text_w, text_h = ctypes.c_int(), ctypes.c_int()
            TTF_SizeUTF8(Notice.font.font, self.text.encode('utf-8'),
                         ctypes.byref(text_w), ctypes.byref(text_h))
            Notice.font.draw(x - text_w.value / 2, top - TEXT_CENTER_Y, self.text, TEXT_COLOR)
