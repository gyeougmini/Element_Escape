from pico2d import *

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


open_canvas(WIDTH, HEIGHT)

while running:
    handle_events()
    clear_canvas()
    update_canvas()
    delay(0.01)

close_canvas()
