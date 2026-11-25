from pico2d import *

# 길을 막고 타오르는 불길: 지나갈 수 없고, 물 공격에 맞아야 꺼짐 (불 공격에는 반응 없음)
# burning.png: 64x64 프레임 4개, 불길이 프레임 아래쪽 끝에 붙어 있음
FLAME_IMAGE = 'sprite_sheet/sprite_sheet_fire/burning.png'
FRAME_SIZE = 64
FRAMES = 4
FPS = 8
OUT_TIME = 0.5  # 물에 맞은 뒤 작아지며 사라지는 시간(초)
# 프레임 안의 불길은 키가 약 30px로 작아서 크게 그림 (캔버스 픽셀 / 그림 픽셀). 아래 10px는 빛 번짐이라
# 불길의 밑동(프레임 아래쪽 끝에서 10px 위)을 칸의 아래쪽 끝에 맞춤
DRAW_SCALE = 1.8
BASE_MARGIN = 10


class Flame:
    image = None

    def __init__(self, background, box):
        # box: 배경 이미지 기준 (left, top, right, bottom). 불길은 이 칸을 막고, 아래쪽 끝에 붙어 그려짐
        if Flame.image is None:
            Flame.image = load_image(FLAME_IMAGE)
        left, top, right, bottom = box
        self.bb = (background.to_canvas_x(left), background.to_canvas_y(bottom),
                   background.to_canvas_x(right), background.to_canvas_y(top))
        self.scale_x = background.to_canvas_x(1) - background.to_canvas_x(0)
        self.scale_y = background.to_canvas_y(0) - background.to_canvas_y(1)
        self.x = (self.bb[0] + self.bb[2]) / 2
        self.bottom = self.bb[1]
        self.anim_time = (left % 7) / 7  # 불길마다 흔들리는 박자가 어긋나도록
        self.out_time = None  # 꺼지기 시작한 뒤 흐른 시간, None이면 타는 중
        self.alive = True     # False가 되면 목록에서 지움

    def is_burning(self):
        return self.out_time is None

    def on_fire_hit(self, damage):
        # 불 공격은 불길에 아무 영향이 없음 (불꽃 이펙트도 남기지 않음)
        return True

    def on_water_hit(self, damage):
        # 물 공격에 맞으면 꺼지기 시작함
        if self.is_burning():
            self.out_time = 0.0

    def update(self, frame_time):
        self.anim_time += frame_time
        if not self.is_burning():
            self.out_time += frame_time
            if self.out_time >= OUT_TIME:
                self.alive = False

    def foot_y(self):
        return self.bottom

    def get_bb(self):
        return self.bb

    def get_obstacle(self):
        """(bb, burnable, on_hit), 꺼지기 시작했으면 지나갈 수 있으므로 None"""
        if not self.is_burning():
            return None
        return self.bb, True, self.on_fire_hit

    def draw(self):
        col = int(self.anim_time * FPS) % FRAMES
        shrink = 1.0 if self.is_burning() else max(0.0, 1 - self.out_time / OUT_TIME)
        w, h = FRAME_SIZE * DRAW_SCALE, FRAME_SIZE * DRAW_SCALE * shrink
        if h <= 0:
            return
        # 꺼질 때는 밑동을 붙인 채로 키가 줄어듦
        frame_bottom = self.bottom - BASE_MARGIN * DRAW_SCALE * shrink
        Flame.image.clip_draw(col * FRAME_SIZE, 0, FRAME_SIZE, FRAME_SIZE,
                              self.x, frame_bottom + h / 2, w, h)
