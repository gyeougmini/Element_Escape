import os

from pico2d import *

import game_framework
import storage_mode

WIDTH, HEIGHT = 1280, 720

# 어느 폴더에서 실행해도 이미지 경로를 찾을 수 있도록 작업 폴더를 고정
os.chdir(os.path.dirname(os.path.abspath(__file__)))

open_canvas(WIDTH, HEIGHT)
game_framework.run(storage_mode)
close_canvas()