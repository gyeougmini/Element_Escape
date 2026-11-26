from pico2d import *

import game_framework
import game_world
from background import Background, WALL, OBJECT
from brute import Brute
from collision import draw_bb, push_out_offset
from glass_bridge import GlassBridge
from hud import ElementHud
from kai import Kai, DIRECTION_ROWS

# 수로(waterway_bg.png): 보일러실의 두 물통을 채워 열린 수로 문으로 들어오면 나오는 단계
WATERWAY_IMAGE = 'sprite_sheet/sprite_sheet_bg/waterway_bg.png'
# 통과할 수 없는 벽과 물체: waterway_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
WATERWAY_OBSTACLES = [
    # 외벽
    (0, 0, 1024, 135, WALL),     # 위 (하수 터널 문 포함)
    (0, 705, 1024, 768, WALL),   # 아래 (오른쪽 아래 입구 포함)
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 가운데를 가로지르는 물길 (난간 포함): 유리판 자리(난간 기둥 사이)만 빼고 막음
    (64, 318, 460, 455, WALL),
    (566, 318, 960, 455, WALL),
    # 물체
    (330, 135, 440, 188, OBJECT),  # 왼쪽 위 기계
    (585, 135, 695, 188, OBJECT),  # 파란 탱크
    (708, 452, 764, 512, OBJECT),  # 물길 아래 제어 상자
    (840, 600, 882, 626, OBJECT),  # 오른쪽 아래 나무 상자
]
# 물길 가운데 유리판: 불(용암구체) 공격에 맞으면 급랭되어 돌 발판이 되고, 그 위로 물길을 건널 수 있음
GLASS_BOX = (448, 332, 576, 448)   # 유리판 그림의 자리
BRIDGE_PATH = (460, 318, 566, 455)  # 유리판이 막고 있는 길 (위아래 난간 기둥 사이)
# 하수 변이체(brute) 2마리: 물길 건너편(위쪽)에서 각자의 줄을 좌우로 순찰. 죽지 않으므로 증기로 시선을 가려 피해야 함
# (발 가운데 x, 발 y, 순찰 왼쪽 끝 x, 오른쪽 끝 x, 처음 걷는 방향), 모두 waterway_bg.png 기준
BRUTES = [
    (300, 222, 100, 920, 1),    # 위쪽 줄 (기계들 앞)
    (760, 292, 100, 920, -1),   # 아래쪽 줄 (물길 난간 앞)
]
KAI_START_IMAGE_POS = (864, 650)  # 시작 위치: 오른쪽 아래 입구 안쪽 (위에서부터의 픽셀 좌표)

show_bbs = False  # F1로 충돌 박스 표시 토글
carried_stats = None  # 이전 단계에서 넘겨받은 (HP, 에너지, 물의 초능력을 얻었는지), 없으면 처음 값
# 디버깅용: 이전 단계 없이 수로부터 시작하면(Element_Escape.py에서 바로 실행) 물 공격을 가진 상태로 시작
DEBUG_START_WITH_WATER = True


def carry_over(kai):
    """이전 단계의 카이 HP, 에너지, 물의 초능력을 이 단계로 넘김 (fade_to 전에 호출)"""
    global carried_stats
    carried_stats = (kai.hp, kai.energy, kai.water_unlocked)


def update_obstacles():
    # 유리판이 돌로 굳으면 지나갈 수 있으므로 매 프레임 합침
    bridge_obstacle = bridge.get_obstacle()
    game_world.obstacles = background.get_obstacles() + ([bridge_obstacle] if bridge_obstacle else [])


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, bridge, brutes, kai, hud
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height, WATERWAY_IMAGE, None, WATERWAY_OBSTACLES)
    bridge = GlassBridge(background, GLASS_BOX, BRIDGE_PATH)
    update_obstacles()
    brutes = [Brute(background.to_canvas_x(x), background.to_canvas_y(y),
                    background.to_canvas_x(left), background.to_canvas_x(right), start_dir)
              for x, y, left, right, start_dir in BRUTES]
    game_world.hittables = brutes  # 죽지 않으므로 늘 공격에 맞음 (피해는 없고 불타는/젖음 상태만)
    hud = ElementHud()
    kai = Kai(0, 0)
    if carried_stats:
        kai.hp, kai.energy, kai.water_unlocked = carried_stats
    elif DEBUG_START_WITH_WATER:
        kai.water_unlocked = True
    start_x, start_y = KAI_START_IMAGE_POS
    kai.place_feet_at(background.to_canvas_x(start_x), background.to_canvas_y(start_y))
    kai.row = DIRECTION_ROWS[(0, 1)]  # 입구에서 안쪽(위)을 바라봄


def finish():
    game_world.objects.clear()
    game_world.hittables = []


def handle_events():
    global show_bbs
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            import title_mode  # 순환 import를 피해 여기서 불러옴
            game_framework.fade_to(title_mode)
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            show_bbs = not show_bbs
        else:
            kai.handle_event(event)


def update(frame_time):
    bridge.update(frame_time)
    update_obstacles()
    offset = push_out_offset(kai.get_bb(), obstacle_bbs())
    if offset:
        kai.x += offset[0]
        kai.y += offset[1]
    kai.update(frame_time, obstacle_bbs())
    for brute in brutes:
        brute.update(frame_time, obstacle_bbs(), kai)
        brute.touch(kai)
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    bridge.draw()  # 돌로 굳은 발판 (배경 그림의 유리판 위에 덮어 그림)
    # 발이 위쪽에 있는 것부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    for actor in sorted([kai] + brutes, key=lambda a: a.foot_y(), reverse=True):
        actor.draw()
    game_world.draw()
    hud.draw(kai.active_elements())
    if show_bbs:
        for bb in obstacle_bbs():
            draw_bb(bb)
        draw_bb(kai.get_bb())
        for brute in brutes:
            draw_bb(brute.get_bb())
            draw_bb(brute.get_hit_bb())
            brute.draw_chase_range()
        for o in game_world.objects:
            if hasattr(o, 'draw_range'):
                o.draw_range()  # 증기가 시야를 가리는 범위
