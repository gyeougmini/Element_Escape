from pico2d import *

LIGHT_IMAGE = 'sprit_sheet_object/bars_gate.png'
# 1024x768 프레임이 4열로 배치된 시트 (14프레임 사용)
# 0: 원래 자물쇠 / 1~3: 점점 달아오름 / 4~7: 자물쇠가 녹아 사라짐 / 8~13: 문이 열림
DARK_SHEET = 'sprit_sheet_object/bars_gate_dark_sheet.png'
FRAME_WIDTH, FRAME_HEIGHT = 1024, 768
SHEET_COLS = 4
SHEET_HEIGHT = 3072

HITS_TO_MELT = 3       # 이만큼 맞으면 자물쇠가 녹음 (1~3단계 = 프레임 1~3)
COOL_TIME = 3.0        # 이 시간(초) 동안 맞지 않을 때마다 한 단계씩 식음 (3 -> 2 -> 1 -> 원래 자물쇠)
MELT_HOLD = 0.3        # 3단계(가장 뜨거운 상태)를 보여주는 시간
OPEN_FPS = 8           # 녹는 애니메이션부터 문이 다 열릴 때까지의 재생 속도
FIRST_OPEN_FRAME = 4
LAST_FRAME = 13

# 충돌 박스: cell_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
DOOR_BOX = (445, 485, 515, 500)        # 닫힌 문 (자물쇠)
OPEN_PANEL_BOX = (446, 485, 462, 543)  # 열린 문짝: 창살 아래(복도 쪽)로 튀어나옴


class Gate:
    """No.07 감방의 창살과 문. 정전 후에는 불 공격으로 자물쇠를 녹여 문을 열 수 있음"""

    def __init__(self, background):
        self.light_image = load_image(LIGHT_IMAGE)
        self.dark_sheet = load_image(DARK_SHEET)
        self.background = background
        self.dark = False
        self.heat = 0            # 맞은 횟수 (0: 원래 자물쇠, 1~3: 달아오른 단계)
        self.cool_time = 0.0
        self.open_time = None    # 녹기 시작한 뒤 흐른 시간, None이면 아직 잠김
        self.door_bb = self.to_bb(DOOR_BOX)
        self.open_panel_bb = self.to_bb(OPEN_PANEL_BOX)

    def to_bb(self, box):
        left, top, right, bottom = box
        bg = self.background
        return (bg.to_canvas_x(left), bg.to_canvas_y(bottom),
                bg.to_canvas_x(right), bg.to_canvas_y(top))

    def set_dark(self, dark):
        self.dark = dark

    def is_melting(self):
        return self.open_time is not None

    def is_open(self):
        return self.is_melting() and self.current_frame() == LAST_FRAME

    def on_fire_hit(self):
        """파이어볼이 문(자물쇠)에 맞았을 때 호출. 처리했으면 True (불꽃 이펙트를 따로 남기지 않음)"""
        if not self.dark or self.is_melting():
            return False  # 정전 전에는 보통 물체처럼 불만 붙음
        self.heat += 1
        self.cool_time = 0.0
        if self.heat >= HITS_TO_MELT:
            self.open_time = 0.0
        return True

    def update(self, frame_time):
        if self.is_melting():
            self.open_time += frame_time
        elif self.heat > 0:
            self.cool_time += frame_time
            if self.cool_time >= COOL_TIME:
                self.heat -= 1
                self.cool_time = 0.0

    def current_frame(self):
        if not self.is_melting():
            return self.heat
        if self.open_time < MELT_HOLD:
            return HITS_TO_MELT
        frame = FIRST_OPEN_FRAME + int((self.open_time - MELT_HOLD) * OPEN_FPS)
        return min(frame, LAST_FRAME)

    def get_obstacles(self):
        # (bb, burnable, on_hit) 목록
        if self.is_open():
            return [(self.open_panel_bb, False, None)]
        return [(self.door_bb, True, self.on_fire_hit)]

    def draw(self):
        w, h = get_canvas_width(), get_canvas_height()
        if not self.dark:
            self.light_image.draw(w // 2, h // 2, w, h)
            return
        frame = self.current_frame()
        col, row = frame % SHEET_COLS, frame // SHEET_COLS
        self.dark_sheet.clip_draw(col * FRAME_WIDTH, SHEET_HEIGHT - (row + 1) * FRAME_HEIGHT,
                                  FRAME_WIDTH, FRAME_HEIGHT, w // 2, h // 2, w, h)
