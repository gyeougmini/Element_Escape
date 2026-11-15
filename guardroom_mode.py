from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from box import make_boxes
from collision import draw_bb, push_out_offset
from hud import ElementHud
from ice import IceBlock
from kai import Kai, DIRECTION_ROWS
from storage_door import StorageDoor
from terminal_lock import TerminalLock

# 간수실(guardroom_bg.png): 창고에서 간수실 문으로 들어오면 나오는 다음 단계
GUARDROOM_IMAGE = 'sprite_sheet/sprite_sheet_bg/guardroom_bg.png'
# 통과할 수 없는 벽과 물체: guardroom_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
GUARDROOM_OBSTACLES = [
    # 외벽
    (0, 0, 1024, 135, WALL),     # 위 (통제실 문 포함)
    (0, 700, 1024, 768, WALL),   # 아래 (입구의 빨간 점선)
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 물체
    (70, 135, 310, 190, OBJECT),   # 왼쪽 위 감시 책상
    (452, 135, 618, 192, OBJECT),  # 사물함
    (650, 135, 686, 190, OBJECT),  # 정수기
    (900, 236, 960, 350, OBJECT),  # 자판기
    (64, 387, 120, 515, OBJECT),   # 왼쪽 벤치
    (85, 580, 270, 632, OBJECT),   # 소파와 탁자
]
# 나무 상자와 얼음 블록: 같은 기준 (몸체 가운데 x, 몸체 아래쪽 끝 y). 바닥 타일(64px)에 맞춰 놓음
# 상자/얼음 사이 틈(12px)은 카이의 발(30px)보다 좁아서 지나갈 수 없음
GUARDROOM_BOX_POSITIONS = [
    (545, 249), (609, 249),   # 사물함 앞
    (161, 442),               # 왼쪽 벤치 옆
    (353, 569),               # 3번 단말기 왼쪽
    (609, 633),               # 아래쪽 줄 왼쪽
]
GUARDROOM_ICE_POSITIONS = [
    (289, 314),               # 1번 단말기 오른쪽
    (672, 441), (799, 441),   # 2번 단말기 양옆
    (736, 505),               # 2번 단말기 아래
    (673, 633), (736, 633),   # 아래쪽 줄 오른쪽
]
# 잠금 단말기 1~3번: (몸체, 단말기 위 불빛, '잠금' 패널의 같은 번호 불빛), 모두 (left, top, right, bottom)
LOCKS = [
    ((206, 220, 244, 316), (224, 210, 226, 212), (734, 100, 740, 106)),  # 1번
    ((718, 348, 756, 444), (736, 338, 738, 340), (746, 100, 752, 106)),  # 2번
    ((398, 476, 436, 572), (416, 466, 418, 468), (758, 100, 764, 106)),  # 3번
]
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지), 없으면 처음 값


def carry_over(kai):
    """이전 단계의 카이 HP와 에너지를 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy)


def update_obstacles():
    # 상자는 타서 무너지고 얼음은 녹으면 지나갈 수 있으므로 배경, 상자, 얼음, 단말기의 장애물을 매 프레임 합침
    object_obstacles = [o.get_obstacle() for o in boxes + ices + locks]
    game_world.obstacles = (background.get_obstacles()
                            + [obstacle for obstacle in object_obstacles if obstacle])


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def all_unlocked():
    return all(lock.is_unlocked() for lock in locks)


def init():
    global background, exit_door, boxes, ices, locks, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, GUARDROOM_IMAGE, None, GUARDROOM_OBSTACLES)
    # 오른쪽 위 통제실 문: 감방의 창고 문과 자리와 그림이 같아서 같은 시트를 씀
    exit_door = StorageDoor(background)
    boxes = make_boxes(background, GUARDROOM_BOX_POSITIONS, {})
    ices = [IceBlock(background, x, bottom) for x, bottom in GUARDROOM_ICE_POSITIONS]
    locks = [TerminalLock(background, *lock) for lock in LOCKS]
    update_obstacles()
    game_world.hittables = []
    hud = ElementHud()
    kai = Kai(0, 0)
    if carried_stats:
        kai.hp, kai.energy = carried_stats
    start_x, start_y = KAI_START_IMAGE_POS
    kai.place_feet_at(background.to_canvas_x(start_x), background.to_canvas_y(start_y))
    kai.row = DIRECTION_ROWS[(0, 1)]  # 입구에서 간수실 안쪽(위)을 바라봄


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


def update(frame_time):
    for box in boxes:
        box.update(frame_time)
    boxes[:] = [box for box in boxes if box.alive]  # 다 타서 사라진 상자는 지움
    for ice in ices:
        ice.update(frame_time)
    ices[:] = [ice for ice in ices if ice.alive]  # 다 녹은 얼음은 지움
    for lock in locks:
        lock.update(frame_time)
    update_obstacles()
    # 서 있던 자리에 장애물이 생기면 끼어서 못 움직이므로 밀어냄
    offset = push_out_offset(kai.get_bb(), obstacle_bbs())
    if offset:
        kai.x += offset[0]
        kai.y += offset[1]
    kai.update(frame_time, obstacle_bbs())
    # 잠금 단말기 세 개가 모두 풀리면 통제실 문이 열림
    if all_unlocked():
        exit_door.open()
    exit_door.update(frame_time)
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    exit_door.draw()
    for lock in locks:
        lock.draw()  # 자물쇠와 불빛 (단말기 몸체는 배경 그림)
    # 발(상자/얼음은 몸체 아래쪽 끝)이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    for actor in sorted([kai] + boxes + ices, key=lambda a: a.foot_y(), reverse=True):
        actor.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
