import os

from pico2d import *

from background import Background
from kai import Kai

WIDTH, HEIGHT = 1280, 720

running = True


def handle_events():
    global running
    events = get_events()
    for event in events:
        if event.type == SDL_QUIT:
            running = False
        elif event.type == SDL_KEYDOWN and event.key == SDLK_ESCAPE:
            running = False
        else:
            kai.handle_event(event)


# 어느 폴더에서 실행해도 sprite_sheet/ 경로를 찾을 수 있도록 작업 폴더를 고정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

open_canvas(WIDTH, HEIGHT)

background = Background(WIDTH, HEIGHT)
kai = Kai(WIDTH // 2, HEIGHT // 2)

last_time = get_time()

while running:
    handle_events()

    now = get_time()
    frame_time = now - last_time
    last_time = now

    kai.update(frame_time)

    clear_canvas()
    background.draw()
    kai.draw()
    update_canvas()
    delay(0.01)

close_canvas()
