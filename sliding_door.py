from pico2d import *

# 배경 그림에 그려진 미닫이 문을 여는 연출: 배경에서 왼쪽/오른쪽 문짝을 잘라 내어 양옆 문틀 속으로 밀어 넣음
# (조명이 켜진 배경처럼 따로 여는 시트가 없는 문에 사용)
OPEN_TIME = 1.2                 # 문이 다 열리기까지 걸리는 시간(초)
INSIDE_COLOR = (14, 14, 20)     # 문이 열리며 드러나는 안쪽 어둠
INSIDE_FLOOR_COLOR = (34, 34, 42)
INSIDE_FLOOR_HEIGHT = 6         # 안쪽 바닥이 보이는 높이 (이미지 픽셀)


def ease_in_out(t):
    return t * t * (3 - 2 * t)


class SlidingDoor:
    """background의 (left, top, right, bottom) 자리에 그려진 두 짝 미닫이 문. 가운데(seam_x)에서 갈라져 열림"""

    def __init__(self, background, box, seam_x):
        # box, seam_x: 배경 이미지 기준 픽셀 좌표 (위에서부터)
        self.bg = background
        self.box = box
        self.seam_x = seam_x
        self.open_time = None  # 열리기 시작한 뒤 흐른 시간, None이면 닫혀 있음

    def open(self):
        if self.open_time is None:
            self.open_time = 0.0

    def is_opening(self):
        return self.open_time is not None

    def is_open(self):
        return self.is_opening() and self.open_time >= OPEN_TIME

    def update(self, frame_time):
        if self.is_opening():
            self.open_time += frame_time

    def to_bb(self, left, top, right, bottom):
        bg = self.bg
        return (bg.to_canvas_x(left), bg.to_canvas_y(bottom), bg.to_canvas_x(right), bg.to_canvas_y(top))

    def draw_image_part(self, src_left, src_right, dst_left):
        # 배경 그림의 [src_left, src_right) 세로 띠를 dst_left 자리에 그림
        if src_right <= src_left:
            return
        _, top, _, bottom = self.box
        image = self.bg.image
        left, b, right, t = self.to_bb(dst_left, top, dst_left + (src_right - src_left), bottom)
        # pico2d는 아래쪽이 원점
        image.clip_draw(int(src_left), image.h - bottom, int(src_right - src_left), bottom - top,
                        (left + right) / 2, (b + t) / 2, right - left, t - b)

    def draw(self):
        if not self.is_opening():
            return  # 닫혀 있으면 배경 그림 그대로
        left, top, right, bottom = self.box
        # 안쪽 어둠과 바닥
        draw_rectangle(*self.to_bb(left, top, right, bottom), *INSIDE_COLOR, 255, filled=True)
        draw_rectangle(*self.to_bb(left, bottom - INSIDE_FLOOR_HEIGHT, right, bottom),
                       *INSIDE_FLOOR_COLOR, 255, filled=True)
        # 문짝이 양옆으로 밀려 들어감: 문틀 밖으로 나간 부분은 그리지 않음
        t = ease_in_out(min(1.0, self.open_time / OPEN_TIME))
        left_w, right_w = self.seam_x - left, right - self.seam_x
        shift_l, shift_r = int(round(left_w * t)), int(round(right_w * t))
        # 왼쪽 문짝: 오른쪽 끝부분만 남아 문틀 왼쪽 끝에 붙음
        self.draw_image_part(left + shift_l, self.seam_x, left)
        # 오른쪽 문짝: 왼쪽 끝부분만 남아 문틀 오른쪽 끝에 붙음
        self.draw_image_part(self.seam_x, right - shift_r, self.seam_x + shift_r)
