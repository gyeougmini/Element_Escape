from pico2d import *

# storage_door_sheet.png: 80x52 프레임 16개 (cell_dark_bg.png의 창고 문 자리에 딱 맞는 크기)
# 0: 닫힌 문(배경과 같음) / 1~15: 경고등이 깜빡이며 문이 열림 / 15: 다 열린 문 (창고 안이 보임)
DOOR_IMAGE = 'sprite_sheet/sprit_sheet_object/storage_door_sheet.png'
FRAME_WIDTH, FRAME_HEIGHT = 80, 52
LAST_FRAME = 15
OPEN_FPS = 10
# 문이 그려질 자리: cell_bg.png 기준 (left, top), 위에서부터의 픽셀 좌표
DOOR_IMAGE_LEFT, DOOR_IMAGE_TOP = 824, 76


class StorageDoor:
    """오른쪽 위 창고 문. 실험 쥐를 모두 잡으면 열림 (닫혀 있을 때는 배경 그림을 그대로 씀)"""

    def __init__(self, background):
        self.image = load_image(DOOR_IMAGE)
        left = background.to_canvas_x(DOOR_IMAGE_LEFT)
        right = background.to_canvas_x(DOOR_IMAGE_LEFT + FRAME_WIDTH)
        top = background.to_canvas_y(DOOR_IMAGE_TOP)
        bottom = background.to_canvas_y(DOOR_IMAGE_TOP + FRAME_HEIGHT)
        self.x, self.y = (left + right) / 2, (bottom + top) / 2
        self.w, self.h = right - left, top - bottom
        self.open_time = None  # 열리기 시작한 뒤 흐른 시간, None이면 닫혀 있음

    def open(self):
        if self.open_time is None:
            self.open_time = 0.0

    def is_opening(self):
        return self.open_time is not None

    def is_open(self):
        return self.is_opening() and self.current_frame() == LAST_FRAME

    def current_frame(self):
        return min(int(self.open_time * OPEN_FPS), LAST_FRAME)

    def update(self, frame_time):
        if self.is_opening():
            self.open_time += frame_time

    def draw(self):
        if not self.is_opening():
            return
        frame = self.current_frame()
        self.image.clip_draw(frame * FRAME_WIDTH, 0, FRAME_WIDTH, FRAME_HEIGHT,
                             self.x, self.y, self.w, self.h)
