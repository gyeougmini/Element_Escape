from pico2d import *

from collision import collide

# potion_hp.png / potion_ep.png: 64x64 프레임 8개, 위아래로 떠다니는 애니메이션 (아래쪽에 그림자)
FRAME_SIZE = 64
FRAMES = 8
FPS = 8
SHADOW_BOTTOM = 3  # 프레임 아래쪽 끝에서 그림자 아래쪽 끝까지의 거리
# 카이의 발이 이 박스(그림자 주변)에 닿으면 주움
PICKUP_HALF_WIDTH = 16
PICKUP_HEIGHT = 14

# 종류별 (이미지, 회복량)
POTIONS = {
    'hp': ('sprit_sheet_object/potion_hp.png', 30),
    'ep': ('sprit_sheet_object/potion_ep.png', 30),
}


class Potion:
    """바닥에 놓인 물약: 카이가 밟으면 HP(hp) 또는 에너지(ep)를 회복하고 사라짐"""
    images = {}

    def __init__(self, kind, x, foot_y):
        path, self.amount = POTIONS[kind]
        if kind not in Potion.images:
            Potion.images[kind] = load_image(path)
        self.kind = kind
        self.image = Potion.images[kind]
        self.x, self.ground_y = x, foot_y  # (x, ground_y): 그림자 아래쪽 끝의 가운데
        self.anim_time = 0.0
        self.alive = True  # False가 되면 play_mode가 목록에서 지움

    def foot_y(self):
        return self.ground_y

    def get_bb(self):
        return (self.x - PICKUP_HALF_WIDTH, self.ground_y,
                self.x + PICKUP_HALF_WIDTH, self.ground_y + PICKUP_HEIGHT)

    def update(self, frame_time, kai):
        self.anim_time += frame_time
        if collide(self.get_bb(), kai.get_bb()):
            self.apply(kai)
            self.alive = False

    def apply(self, kai):
        if self.kind == 'hp':
            kai.hp = min(kai.max_hp, kai.hp + self.amount)
        else:
            kai.energy = min(kai.max_energy, kai.energy + self.amount)

    def draw(self):
        col = int(self.anim_time * FPS) % FRAMES
        self.image.clip_draw(col * FRAME_SIZE, 0, FRAME_SIZE, FRAME_SIZE,
                             self.x, self.ground_y - SHADOW_BOTTOM + FRAME_SIZE / 2)
