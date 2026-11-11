from pico2d import *

import game_framework
import game_world
from background import Background
from box import make_boxes
from collision import draw_bb, push_out_offset
from dialogue import DialogueBox, LEFT_SLANT_LAYOUT
from gate import Gate
from hud import ElementHud
from kai import Kai
from notice import Notice
from rat import spawn_rats

show_bbs = False  # F1로 충돌 박스 표시 토글
KAI_START_IMAGE_POS = (560, 305)  # 시작 위치: cell_bg.png 바닥의 '07' 글자 (위에서부터의 픽셀 좌표)
# 시작 안내: 화면이 밝아진 뒤 나타나고, 안내가 사라질 때까지 모든 입력을 막음
MOVE_NOTICE_TEXT = '플레이어 이동: WASD'
MOVE_NOTICE_DELAY = 0.5  # game_framework.FADE_TIME과 같게 해서 화면이 다 밝아진 뒤 등장
MOVE_NOTICE_HOLD = 2.0
LIGHTS_OFF_DELAY = 3.0  # 안내가 사라지고 이 시간(초)이 지나면 조명이 꺼짐 (cell_dark_bg.png로 교체)
# 정전 후 나오는 ARC Lab 방송: 정전부터 대화창이 닫힐 때까지 플레이어 조작을 막음
BLACKOUT_TEXT = '비상. 정전 발생.\n경계모드 활성화'
BLACKOUT_DIALOGUE_DELAY = 1.0  # 정전되고 이 시간(초)이 지나면 대화창이 나옴
# ARC Lab 대화창을 닫으면 나오는 안내: 이동 안내와 같은 방식으로 입력을 막고 보여줌
FIRE_NOTICE_TEXT = '불 공격: Q'
FIRE_NOTICE_DELAY = 0.3
FIRE_NOTICE_HOLD = 2.0
RAT_COUNT = 5
# 쥐가 나타나는 철창 바깥 구역: cell_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
RAT_AREAS = [
    (70, 520, 955, 700),   # 아래쪽 복도
    (775, 140, 955, 520),  # 오른쪽 복도 (EXIT 쪽)
]
DIALOGUE_SCALE = 1.5
DIALOGUE_MARGIN = 40  # 화면 오른쪽 아래 모서리에서 대화창까지의 거리


def make_arc_dialogue():
    width = get_canvas_width()
    box_w, box_h = 416 * DIALOGUE_SCALE, 176 * DIALOGUE_SCALE
    box = DialogueBox('sprite_sheet_dialugue/dialogue_skyblue_box.png',
                      'sprite_sheet_dialugue/dialogue_skyblue_arrow.png',
                      width - DIALOGUE_MARGIN - box_w / 2, DIALOGUE_MARGIN + box_h / 2,
                      DIALOGUE_SCALE, LEFT_SLANT_LAYOUT)
    box.set_text(BLACKOUT_TEXT)
    return box


def update_obstacles():
    # 문은 열리면 충돌 박스가 바뀌므로 배경, 문, 상자의 장애물을 매 프레임 합침
    game_world.obstacles = (background.get_obstacles() + gate.get_obstacles()
                            + [box.get_obstacle() for box in boxes])


def obstacle_bbs():
    return [bb for bb, _, _ in game_world.obstacles]


def init():
    global background, gate, boxes, kai, rats, hud, notice, after_notice_time, lights_off, dialogue, dialogue_wait
    hud = ElementHud()
    notice = Notice(MOVE_NOTICE_TEXT, MOVE_NOTICE_HOLD, MOVE_NOTICE_DELAY)
    after_notice_time = 0.0
    lights_off = False
    dialogue = None  # 지금 떠 있는 대화창
    dialogue_wait = None  # 정전 후 대화창이 나올 때까지 남은 시간(초), 기다리는 중이 아니면 None
    width, height = get_canvas_width(), get_canvas_height()
    background = Background(width, height)
    gate = Gate(background)
    boxes = make_boxes(background)
    kai = Kai(0, 0)
    start_x, start_y = KAI_START_IMAGE_POS
    kai.place_feet_at(background.to_canvas_x(start_x), background.to_canvas_y(start_y))
    update_obstacles()
    areas = [(background.to_canvas_x(left), background.to_canvas_y(bottom),
              background.to_canvas_x(right), background.to_canvas_y(top))
             for left, top, right, bottom in RAT_AREAS]
    rats = spawn_rats(RAT_COUNT, areas, obstacle_bbs())
    game_world.hittables = list(rats)


def finish():
    game_world.objects.clear()
    game_world.hittables = []


def handle_events():
    global show_bbs, dialogue, notice
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif not notice.is_done() or dialogue_wait is not None:
            continue  # 안내 중이나 정전 후 대화창을 기다리는 동안에는 키보드/마우스 입력을 모두 무시
        elif dialogue:
            # 대화 중에는 클릭만 받음: 출력 중이면 한 번에 보여주고, 다 나온 상태면 닫음
            if event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
                if dialogue.is_complete():
                    dialogue = None
                    notice = Notice(FIRE_NOTICE_TEXT, FIRE_NOTICE_HOLD, FIRE_NOTICE_DELAY)
                else:
                    dialogue.show_all()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            import title_mode  # title_mode가 play_mode를 import하므로 순환 import를 피해 여기서 불러옴
            game_framework.fade_to(title_mode)
            return
        elif event.type == SDL_KEYDOWN and event.key == SDLK_F1:
            show_bbs = not show_bbs
        else:
            kai.handle_event(event)


def update(frame_time):
    global after_notice_time, lights_off, dialogue, dialogue_wait
    notice.update(frame_time)
    if notice.is_done() and not lights_off:
        after_notice_time += frame_time
        if after_notice_time >= LIGHTS_OFF_DELAY:
            lights_off = True
            background.set_dark(True)
            gate.set_dark(True)
            kai.stop()
            dialogue_wait = BLACKOUT_DIALOGUE_DELAY
    if dialogue_wait is not None:
        dialogue_wait -= frame_time
        if dialogue_wait <= 0:
            dialogue_wait = None
            dialogue = make_arc_dialogue()
    if dialogue:
        dialogue.update(frame_time)
    gate.update(frame_time)
    update_obstacles()
    # 문이 열리며 생긴 문짝 박스처럼 캐릭터가 서 있던 자리에 장애물이 생기면 끼어서 못 움직이므로 밀어냄
    for actor in [kai] + rats:
        offset = push_out_offset(actor.get_bb(), obstacle_bbs())
        if offset:
            actor.x += offset[0]
            actor.y += offset[1]
    kai.update(frame_time, obstacle_bbs())
    # 철창 문이 열리기 전에는 쥐가 카이를 추적하지 않고 돌아다니기만 함
    chase_target = kai if gate.is_open() else None
    for rat in rats:
        rat.update(frame_time, obstacle_bbs(), chase_target)
        rat.touch(kai)
    # 기절 연출이 끝난 쥐는 지우고, HP가 남은 쥐만 파이어볼에 맞도록 함
    rats[:] = [rat for rat in rats if rat.alive]
    game_world.hittables = [rat for rat in rats if not rat.is_dead()]
    game_world.update(frame_time)
    hud.update(frame_time, kai)


def draw():
    background.draw()
    # 발이 위쪽에 있는 캐릭터(와 상자)부터 그려서 아래쪽(화면 앞쪽)이 위에 겹치게 함
    # 창살 뒤(감방 안)에 있는 캐릭터는 창살보다 먼저 그려서 창살에 가려지게 함
    actors = sorted([kai] + rats + boxes, key=lambda a: a.foot_y(), reverse=True)
    for actor in actors:
        if actor.foot_y() > background.gate_base_y:
            actor.draw()
    gate.draw()
    for actor in actors:
        if actor.foot_y() <= background.gate_base_y:
            actor.draw()
    # 파이어볼과 불꽃 이펙트는 항상 맨 위에 그림
    game_world.draw()
    hud.draw(kai.active_elements())
    notice.draw()
    if dialogue:
        dialogue.draw()
    if show_bbs:
        for bb, _, _ in game_world.obstacles:
            draw_bb(bb)
        draw_bb(kai.get_bb())
        for rat in rats:
            draw_bb(rat.get_bb())
            draw_bb(rat.get_hit_bb())
            rat.draw_chase_range()
        for o in game_world.objects:
            if hasattr(o, 'get_bb'):
                draw_bb(o.get_bb())
