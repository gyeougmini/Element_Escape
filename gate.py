from pico2d import *

LIGHT_IMAGE = 'sprite_sheet/sprit_sheet_object/bars_gate.png'
# 1024x768 프레임이 4열로 배치된 시트 (14프레임 사용)
# 0: 원래 자물쇠 / 1~3: 점점 달아오름 / 4~7: 자물쇠가 녹아 사라짐 / 8~13: 문이 열림
DARK_SHEET = 'sprite_sheet/sprit_sheet_object/bars_gate_dark_sheet.png'
FRAME_WIDTH, FRAME_HEIGHT = 1024, 768
SHEET_COLS = 4
SHEET_HEIGHT = 3072

LOCK_HP = 25           # 받은 피해가 이만큼 쌓이면 자물쇠가 녹음
HEAT_STAGES = 3        # 달아오른 단계 수 (프레임 1~3): 받은 피해가 LOCK_HP의 1/3, 2/3, 전부일 때
COOL_TIME = 3.0        # 이 시간(초) 동안 맞지 않을 때마다 COOL_AMOUNT만큼 회복 (한 단계씩 식음)
COOL_AMOUNT = 10
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
        self.damage = 0          # 자물쇠가 받은 피해 (LOCK_HP 이상이면 녹음)
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

    def heat_stage(self):
        # 받은 피해에 따른 달아오른 단계 (0: 원래 자물쇠 ~ HEAT_STAGES: 녹기 직전)
        return min(HEAT_STAGES, int(self.damage / (LOCK_HP / HEAT_STAGES)))

    def on_fire_hit(self, damage):
        """파이어볼이 문(자물쇠)에 맞았을 때 호출. 처리했으면 True (불꽃 이펙트를 따로 남기지 않음)"""
        if not self.dark or self.is_melting():
            return False  # 정전 전에는 보통 물체처럼 불만 붙음
        self.damage += damage
        self.cool_time = 0.0
        if self.damage >= LOCK_HP:
            self.open_time = 0.0
        return True

    def update(self, frame_time):
        if self.is_melting():
            self.open_time += frame_time
        elif self.damage > 0:
            self.cool_time += frame_time
            if self.cool_time >= COOL_TIME:
                self.damage = max(0, self.damage - COOL_AMOUNT)
                self.cool_time = 0.0

    def current_frame(self):
        if not self.is_melting():
            return self.heat_stage()
        if self.open_time < MELT_HOLD:
            return HEAT_STAGES
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
