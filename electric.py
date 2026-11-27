from pico2d import *

import game_world
from fire import Fireball, OneShotEffect

# electric.png (576x768)
#   위쪽 8줄(y 0~511): 날아가는 전기 구슬. fireball_sheet.png와 같은 배치 (4열, 프레임 64x64, 행은 오른쪽부터 반시계 방향으로 45도씩)
#   y 512~575: 발사 섬광 3프레임 (64x64)
#   y 576~671: 맞았을 때 터지는 효과 6프레임 (96x96)
#   그 아래: 번개 줄기, 작은 스파크 (아직 쓰지 않음)
ELECTRIC_IMAGE = 'sprite_sheet/sprite_sheet_elec/electric.png'
ELECTRIC_SHEET_HEIGHT = 768
ELECTRIC_SPEED = 600     # 초당 이동 픽셀 (불, 물보다 빠름)
ELECTRIC_DAMAGE = 8      # 한 발당 피해
ELECTRIC_FPS = 16

LAUNCH_SIZE, LAUNCH_FRAMES, LAUNCH_FPS = 64, 3, 20
LAUNCH_CLIP_BOTTOM = ELECTRIC_SHEET_HEIGHT - 576   # 발사 섬광 줄의 아래쪽 끝 (pico2d는 아래쪽이 원점)
IMPACT_SIZE, IMPACT_FRAMES, IMPACT_FPS = 96, 6, 15
IMPACT_CLIP_BOTTOM = ELECTRIC_SHEET_HEIGHT - 672   # 터지는 효과 줄의 아래쪽 끝


class ElectricBall(Fireball):
    """전기 공격: 파이어볼처럼 날아가 맞은 대상에게 피해를 줌. 반응은 대상의 on_electric_hit이 정함.
    상자, 얼음, 자물쇠 같은 물체에는 반응 없이 터지기만 함"""
    image = None
    IMAGE_PATH = ELECTRIC_IMAGE
    SHEET_HEIGHT = ELECTRIC_SHEET_HEIGHT
    SPEED = ELECTRIC_SPEED
    DAMAGE = ELECTRIC_DAMAGE
    FPS = ELECTRIC_FPS

    def hit_target(self, target):
        self.alive = False
        game_world.add(ElectricImpact(self.x, self.y))
        target.on_electric_hit(self.dir_x, self.dir_y, self.DAMAGE)

    def hit(self, burnable, on_hit):
        # 물체에 맞으면 불 공격용 반응(on_hit: 불붙음, 녹음 등)은 부르지 않음.
        # 대신 그 물체가 전기에 반응하면(on_electric_hit이 있으면) 그것을 부름
        self.alive = False
        game_world.add(ElectricImpact(self.x, self.y))
        owner = getattr(on_hit, '__self__', None)  # on_hit은 물체의 메서드이므로 그 물체를 찾음
        if owner is not None and hasattr(owner, 'on_electric_hit'):
            owner.on_electric_hit(self.DAMAGE)


class ElectricLaunch(OneShotEffect):
    def __init__(self, x, y):
        super().__init__(ELECTRIC_IMAGE, x, y, LAUNCH_SIZE, LAUNCH_FRAMES, LAUNCH_FPS, LAUNCH_CLIP_BOTTOM)


class ElectricImpact(OneShotEffect):
    def __init__(self, x, y):
        super().__init__(ELECTRIC_IMAGE, x, y, IMPACT_SIZE, IMPACT_FRAMES, IMPACT_FPS, IMPACT_CLIP_BOTTOM)
