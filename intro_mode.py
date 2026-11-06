from pico2d import *

import game_framework
import play_mode
from dialogue import DialogueBox

# 게임 시작 전 검은 화면에서 나오는 카이의 대사 (순서대로 출력)
LINES = [
    '얼마나 잠들어있던거지...',
]

DIALOGUE_SCALE = 1.5
DIALOGUE_MARGIN = 40  # 화면 왼쪽 아래 모서리에서 대화창까지의 거리


def init():
    global dialogue, line_index
    box_w, box_h = 416 * DIALOGUE_SCALE, 176 * DIALOGUE_SCALE
    dialogue = DialogueBox('sprite_sheet_dialugue/dialogue_red_box.png',
                           'sprite_sheet_dialugue/dialogue_red_arrow_.png',
                           DIALOGUE_MARGIN + box_w / 2, DIALOGUE_MARGIN + box_h / 2, DIALOGUE_SCALE)
    line_index = 0
    dialogue.set_text(LINES[line_index])


def finish():
    pass


def next_line():
    global line_index
    line_index += 1
    if line_index < len(LINES):
        dialogue.set_text(LINES[line_index])
    else:
        game_framework.fade_to(play_mode)


def handle_events():
    for event in get_events():
        if event.type == SDL_QUIT:
            game_framework.quit()
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            game_framework.quit()
        elif event.type == SDL_MOUSEBUTTONDOWN and event.button == SDL_BUTTON_LEFT:
            # 출력 중이면 문구를 한 번에 보여주고, 다 나온 상태면 다음으로
            if dialogue.is_complete():
                next_line()
            else:
                dialogue.show_all()


def update(frame_time):
    dialogue.update(frame_time)


def draw():
    # pico2d의 clear_canvas는 회색 격자로 지우므로 검은색으로 직접 채운 뒤 대화창만 그림
    draw_rectangle(0, 0, get_canvas_width(), get_canvas_height(), 0, 0, 0, 255, filled=True)
    dialogue.draw()
