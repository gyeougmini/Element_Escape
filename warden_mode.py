from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from collision import draw_bb, push_out_offset
from hud import ElementHud
from kai import Kai, DIRECTION_ROWS
from notice import Notice
from sliding_door import SlidingDoor
from warden import Warden
from water_capsule import WaterCapsule

# 워든 맵(warden_bg.png): 간수실에서 통제실 문으로 들어오면 나오는 보스 단계
WARDEN_MAP_IMAGE = 'sprite_sheet/sprite_sheet_bg/warden_bg.png'
# 통과할 수 없는 벽과 물체: warden_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
WARDEN_MAP_OBSTACLES = [
    # 외벽
    (0, 0, 1024, 135, WALL),     # 위 (보일러실 문 포함)
    (0, 700, 1024, 768, WALL),   # 아래 (오른쪽 아래 입구 포함)
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 물체
    (72, 135, 310, 188, OBJECT),   # 왼쪽 위 제어 콘솔
    (385, 135, 513, 188, OBJECT),  # W-01 격납고 받침대
    (598, 135, 683, 188, OBJECT),  # 캡슐 장치
    (120, 636, 155, 668, OBJECT),  # 왼쪽 아래 부서진 소형 로봇
]
KAI_START_IMAGE_POS = (864, 650)     # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)
WARDEN_START_IMAGE_POS = (512, 420)  # 워든 시작 위치: 바닥의 W-01 원 가운데
# 오른쪽 위 보일러실 문: 배경에 그려진 두 짝 미닫이 문 (left, top, right, bottom)과 가운데 갈라지는 x
BOILER_DOOR_BOX = (824, 76, 904, 128)
BOILER_DOOR_SEAM_X = 864
# 물의 초능력 알약을 먹었을 때 나오는 안내
WATER_NOTICE_TEXT = '물의 초능력을 얻었다! 물 공격: E'
WATER_NOTICE_HOLD = 2.5

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지), 없으면 처음 값


def carry_over(kai):
    """이전 단계의 카이 HP와 에너지를 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy)


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, kai, warden, capsule, boiler_door, notice, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, WARDEN_MAP_IMAGE, None, WARDEN_MAP_OBSTACLES)
    game_world.obstacles = background.get_obstacles()
    game_world.hittables = []
    hud = ElementHud()
    kai = Kai(0, 0)
    if carried_stats:
        kai.hp, kai.energy = carried_stats
    start_x, start_y = KAI_START_IMAGE_POS
    kai.place_feet_at(background.to_canvas_x(start_x), background.to_canvas_y(start_y))
    kai.row = DIRECTION_ROWS[(0, 1)]  # 입구에서 안쪽(위)을 바라봄
    warden = Warden(0, 0)
    start_x, start_y = WARDEN_START_IMAGE_POS
    warden.place_feet_at(background.to_canvas_x(start_x), background.to_canvas_y(start_y))
    game_world.hittables = [warden]  # 파이어볼에 맞는 대상
    capsule = WaterCapsule(background)
    boiler_door = SlidingDoor(background, BOILER_DOOR_BOX, BOILER_DOOR_SEAM_X)
    notice = None  # 알약을 먹으면 나오는 안내


def finish():
    game_world.objects.clear()
    game_world.hittables = []


def handle_events():
    global show_bbs
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            import title_mode  # title_mode가 play_mode를 거쳐 이 모듈을 import하므로 순환 import를 피해 여기서 불러옴
            game_framework.fade_to(title_mode)
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            show_bbs = not show_bbs
        else:
            kai.handle_event(event)


def eat_water_pill():
    global notice
    kai.water_unlocked = True
    notice = Notice(WATER_NOTICE_TEXT, WATER_NOTICE_HOLD)


def update(frame_time):
    # 서 있던 자리에 장애물이 생기면 끼어서 못 움직이므로 밀어냄
    for actor in (kai, warden):
        offset = push_out_offset(actor.get_bb(), obstacle_bbs())
        if offset:
            actor.x += offset[0]
            actor.y += offset[1]
    kai.update(frame_time, obstacle_bbs())
    # 워든은 항상 카이를 추적하고, 가까워지면 더 빨리 다가옴
    warden.update(frame_time, obstacle_bbs(), kai)
    warden.touch(kai)
    game_world.hittables = [] if warden.is_dead() else [warden]  # 쓰러지면 파이어볼이 지나감
    # 워든이 쓰러지는 연출이 끝나면 보일러실 문이 열리고, 캡슐 장치의 유리관이 열려 알약이 나와 떠다님
    if warden.is_death_done():
        boiler_door.open()
        capsule.open()
    boiler_door.update(frame_time)
    if capsule.update(frame_time, kai):
        eat_water_pill()
    if notice:
        notice.update(frame_time)
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    boiler_door.draw()      # 열리는 보일러실 문과
    capsule.draw_machine()  # 유리관 (둘 다 벽 그림의 일부라서 배경 바로 위에 그림)
    # 발이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    for actor in sorted([kai, warden, capsule], key=lambda a: a.foot_y(), reverse=True):
        actor.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    if notice:
        notice.draw()
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
        draw_bb(warden.get_bb())
        draw_bb(warden.get_hit_bb())
        warden.draw_dash_range()
        if capsule.is_floating():
            draw_bb(capsule.get_bb())
