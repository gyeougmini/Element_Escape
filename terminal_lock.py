from pico2d import *

# 간수실의 잠금 단말기(1~3번): 단말기 몸체는 배경 그림, 아래쪽 판의 자물쇠는 lock_melt_sheet.png로 그림
# lock_melt_sheet.png: 64x64 프레임 8개
# 0: 자물쇠 / 1~3: 불이 붙어 점점 달아오름 / 4~6: 녹아내림 / 7: 녹아 없어진 자리 (식은 웅덩이와 연기)
LOCK_IMAGE = 'sprite_sheet/sprit_sheet_object/lock_melt_sheet.png'
FRAME_SIZE = 64
LOCK_CENTER_IN_FRAME = (33, 29)  # 프레임 안에서 자물쇠(0번 프레임) 몸체의 가운데, 위에서부터의 픽셀 좌표
LOCK_OFFSET_Y = 64               # 단말기 몸체 위쪽 끝에서 자물쇠 가운데까지의 거리 (아래쪽 판의 가운데)
HEAT_STAGES = 3                  # 달아오른 단계 수 (프레임 1~3): 받은 피해가 LOCK_HP의 1/3, 2/3, 전부일 때
MELT_HOLD = 0.3                  # 가장 뜨거운 상태(3번 프레임)를 보여주는 시간
MELT_FPS = 6                     # 녹아내리는 프레임(4~7) 재생 속도
FIRST_MELT_FRAME, LAST_FRAME = 4, 7

# 불 공격으로 LOCK_HP만큼 피해를 주면 자물쇠가 녹기 시작하고, 다 녹아 없어지면 잠금이 풀림
# 녹기 전에 COOL_TIME 동안 맞지 않으면 식어서 원래 자물쇠로 돌아감
# 잠금이 풀리면 단말기 위 불빛과 '잠금' 패널의 같은 번호 불빛이 빨강 -> 초록으로 바뀜
LOCK_HP = 30            # 파이어볼(10) 세 발: 한 발마다 한 단계씩 달아오르고(프레임 1, 2), 세 번째에 녹음
COOL_TIME = 2.0         # 달아오른 뒤 이 시간(초) 동안 불 공격을 받지 않으면 식어서 원래 자물쇠로 돌아감
GREEN = (60, 255, 120)
GLOW_ALPHA = 70         # 불빛 둘레에 번지는 빛의 투명도
GLOW_SIZE = 3           # 불빛 둘레로 번지는 빛의 두께 (이미지 픽셀)


class TerminalLock:
    """잠금 단말기: 지나갈 수 없는 물체. 불 공격에 맞으면 자물쇠가 달아올라 녹고, 다 녹으면 잠금이 풀림"""
    image = None

    def __init__(self, background, body_box, light_box, panel_light_box):
        # 세 박스 모두 배경 이미지 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
        if TerminalLock.image is None:
            TerminalLock.image = load_image(LOCK_IMAGE)
        self.background = background
        self.bb = self.to_bb(body_box)
        self.lights = [light_box, panel_light_box]
        self.scale_x = background.to_canvas_x(1) - background.to_canvas_x(0)
        self.scale_y = background.to_canvas_y(0) - background.to_canvas_y(1)
        # 프레임이 그려질 가운데: 자물쇠 몸체가 단말기 아래쪽 판 가운데에 오도록 맞춤
        left, top, right, _ = body_box
        lock_x, lock_y = (left + right) / 2, top + LOCK_OFFSET_Y
        frame_cx = lock_x - LOCK_CENTER_IN_FRAME[0] + FRAME_SIZE / 2
        frame_cy = lock_y - LOCK_CENTER_IN_FRAME[1] + FRAME_SIZE / 2
        self.x, self.y = background.to_canvas_x(frame_cx), background.to_canvas_y(frame_cy)
        self.damage = 0
        self.cool_time = 0.0   # 마지막으로 맞은 뒤 흐른 시간 (달아오른 상태에서만 셈)
        self.melt_time = None  # 녹기 시작한 뒤 흐른 시간, None이면 아직 녹지 않음

    def to_bb(self, box, grow=0):
        left, top, right, bottom = box
        bg = self.background
        return (bg.to_canvas_x(left - grow), bg.to_canvas_y(bottom + grow),
                bg.to_canvas_x(right + grow), bg.to_canvas_y(top - grow))

    def is_melting(self):
        return self.melt_time is not None

    def is_unlocked(self):
        # 자물쇠가 다 녹아 없어져야 잠금이 풀림
        return self.is_melting() and self.current_frame() == LAST_FRAME

    def heat_stage(self):
        # 받은 피해에 따른 달아오른 단계 (0: 원래 자물쇠 ~ HEAT_STAGES: 녹기 직전)
        return min(HEAT_STAGES, int(self.damage / (LOCK_HP / HEAT_STAGES)))

    def on_fire_hit(self, damage):
        """파이어볼에 맞았을 때 호출. 단말기가 직접 반응하므로 True (불꽃 이펙트를 따로 남기지 않음)"""
        if not self.is_melting():
            self.damage += damage
            self.cool_time = 0.0
            if self.damage >= LOCK_HP:
                self.melt_time = 0.0
        return True

    def current_frame(self):
        if not self.is_melting():
            return self.heat_stage()
        if self.melt_time < MELT_HOLD:
            return HEAT_STAGES
        frame = FIRST_MELT_FRAME + int((self.melt_time - MELT_HOLD) * MELT_FPS)
        return min(frame, LAST_FRAME)

    def update(self, frame_time):
        if self.is_melting():
            self.melt_time += frame_time
        elif self.damage > 0:
            # 한두 번 맞고 COOL_TIME 동안 더 맞지 않으면 다 식어서 처음부터 다시 맞혀야 함
            self.cool_time += frame_time
            if self.cool_time >= COOL_TIME:
                self.damage = 0
                self.cool_time = 0.0

    def foot_y(self):
        return self.bb[1]

    def get_obstacle(self):
        # 자물쇠가 녹아도 단말기는 그대로 남아 있으므로 계속 막힘
        return self.bb, True, self.on_fire_hit

    def draw(self):
        size_w, size_h = FRAME_SIZE * self.scale_x, FRAME_SIZE * self.scale_y
        TerminalLock.image.clip_draw(self.current_frame() * FRAME_SIZE, 0, FRAME_SIZE, FRAME_SIZE,
                                     self.x, self.y, size_w, size_h)
        if not self.is_unlocked():
            return  # 잠겨 있으면 배경의 빨간 불빛을 그대로 보여줌
        for light in self.lights:
            draw_rectangle(*self.to_bb(light, GLOW_SIZE), *GREEN, GLOW_ALPHA, filled=True)
            draw_rectangle(*self.to_bb(light), *GREEN, 255, filled=True)
