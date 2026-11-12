from pico2d import *

BG_IMAGE_WIDTH, BG_IMAGE_HEIGHT = 1024, 768
GATE_BASE_IMAGE_Y = 500  # 창살 아래쪽 끝의 y (위에서부터, 픽셀)

WALL, OBJECT = False, True  # 파이어볼에 맞았을 때 불이 붙는지(burnable)

# 통과할 수 없는 벽과 물체: cell_bg.png 기준 (left, top, right, bottom), 위에서부터의 픽셀 좌표
OBSTACLES = [
    # 외벽
    (0, 0, 1024, 130, WALL),     # 위
    (0, 705, 1024, 768, WALL),   # 아래
    (0, 0, 64, 768, WALL),       # 왼쪽
    (960, 0, 1024, 768, WALL),   # 오른쪽
    # 감방 사이 벽
    (256, 0, 320, 500, WALL),    # No.12 | No.07
    (704, 0, 768, 510, WALL),    # No.07 | 복도
    # 창살 (아래쪽 끝 부분만). No.07 문(자물쇠)은 열리고 닫히므로 gate.py에서 관리
    (64, 485, 256, 500, WALL),   # No.12
    (320, 485, 445, 500, WALL),  # No.07 문 왼쪽
    (515, 485, 704, 500, WALL),  # No.07 문 오른쪽
    # No.12 감방
    (84, 130, 176, 295, OBJECT),   # 침대
    # No.07 감방
    (330, 132, 424, 298, OBJECT),  # 침대
    (440, 140, 494, 214, OBJECT),  # 모니터 테이블
    (430, 250, 460, 272, OBJECT),  # 링거 거치대 받침
    (580, 105, 626, 142, OBJECT),  # 세면대
    (640, 100, 690, 175, OBJECT),  # 변기
    (598, 450, 655, 480, OBJECT),  # 식판
    # 복도
    (78, 578, 188, 672, OBJECT),   # 시약 카트
]


class Background:
    def __init__(self, width, height, image_path='sprite_sheet/sprite_sheet_bg/cell_bg.png',
                 dark_image_path='sprite_sheet/sprite_sheet_bg/cell_dark_bg.png', obstacles=OBSTACLES):
        # 배경 그림과 그 위의 충돌 박스 목록. 기본값은 감방(cell_bg.png)
        self.light_image = load_image(image_path)
        # 배치는 같고 조명만 꺼진 버전: 충돌 박스는 그대로 사용 (없으면 밝은 그림을 그대로 씀)
        self.dark_image = load_image(dark_image_path) if dark_image_path else self.light_image
        self.image = self.light_image
        self.width, self.height = width, height
        # 창살 아래쪽 끝의 캔버스 y 좌표: 이보다 위에 발이 있으면 감방 안(창살 뒤)
        self.gate_base_y = self.to_canvas_y(GATE_BASE_IMAGE_Y)
        # (bb, burnable, on_hit): on_hit은 파이어볼에 맞았을 때 부를 함수 (배경 물체는 없음)
        self.obstacles = [((self.to_canvas_x(left), self.to_canvas_y(bottom),
                            self.to_canvas_x(right), self.to_canvas_y(top)), burnable, None)
                          for left, top, right, bottom, burnable in obstacles]

    def to_canvas_x(self, image_x):
        return image_x * self.width / BG_IMAGE_WIDTH

    def to_canvas_y(self, image_y):
        # 이미지는 위에서부터, pico2d는 아래에서부터 y를 셈
        return (BG_IMAGE_HEIGHT - image_y) * self.height / BG_IMAGE_HEIGHT

    def set_dark(self, dark):
        self.image = self.dark_image if dark else self.light_image

    def get_obstacles(self):
        return self.obstacles

    def draw(self):
        self.image.draw(self.width // 2, self.height // 2, self.width, self.height)
