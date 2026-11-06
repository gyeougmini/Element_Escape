from pico2d import *

FONT_PATH = 'C:/Windows/Fonts/malgun.ttf'  # 맑은 고딕 (한글 표시용)
FONT_SIZE = 26
TEXT_COLOR = (235, 235, 235)
LINE_SPACING = 40
CHAR_INTERVAL = 0.07  # 한 글자가 나오는 간격(초)

# 대화창 이미지(416x176) 안에서의 위치, 이미지 왼쪽 위 기준 픽셀
TEXT_TOP = 72          # 첫 줄 글자 중심의 y
# 빨간 창(카이)은 오른쪽이, 하늘색/초록 창은 왼쪽이 비스듬하므로 글자 시작 x와 화살표 위치가 다름
RIGHT_SLANT_LAYOUT = {'text_left': 26, 'arrow_center': (352, 152)}
LEFT_SLANT_LAYOUT = {'text_left': 100, 'arrow_center': (390, 152)}

ARROW_WIDTH, ARROW_HEIGHT = 24, 20  # 화살표 시트: 2프레임
ARROW_FRAMES = 2
ARROW_FPS = 3


class DialogueBox:
    """대화창에 문구를 한 글자씩 출력. 다 출력되면 다음을 알리는 화살표가 깜빡임"""
    font = None

    def __init__(self, box_path, arrow_path, x, y, scale, layout=RIGHT_SLANT_LAYOUT):
        if DialogueBox.font is None:
            DialogueBox.font = load_font(FONT_PATH, FONT_SIZE)
        self.box = load_image(box_path)
        self.arrow = load_image(arrow_path)
        self.x, self.y, self.scale = x, y, scale
        self.text_left = layout['text_left']
        self.arrow_center = layout['arrow_center']
        self.text = ''
        self.time = 0.0

    def set_text(self, text):
        self.text = text
        self.time = 0.0

    def shown_count(self):
        return min(int(self.time / CHAR_INTERVAL), len(self.text))

    def is_complete(self):
        return self.shown_count() >= len(self.text)

    def show_all(self):
        self.time = len(self.text) * CHAR_INTERVAL

    def update(self, frame_time):
        self.time += frame_time

    def to_canvas(self, image_x, image_y):
        # 대화창 이미지 좌표(왼쪽 위 기준)를 캔버스 좌표로 변환
        left = self.x - self.box.w * self.scale / 2
        top = self.y + self.box.h * self.scale / 2
        return left + image_x * self.scale, top - image_y * self.scale

    def draw(self):
        self.box.draw(self.x, self.y, self.box.w * self.scale, self.box.h * self.scale)
        text_x, text_y = self.to_canvas(self.text_left, TEXT_TOP)
        for i, line in enumerate(self.text[:self.shown_count()].split('\n')):
            if line:  # pico2d는 빈 문자열을 그리면 오류가 남
                DialogueBox.font.draw(text_x, text_y - i * LINE_SPACING, line, TEXT_COLOR)
        if self.is_complete():
            frame = int(self.time * ARROW_FPS) % ARROW_FRAMES
            arrow_x, arrow_y = self.to_canvas(*self.arrow_center)
            self.arrow.clip_draw(frame * ARROW_WIDTH, 0, ARROW_WIDTH, ARROW_HEIGHT, arrow_x, arrow_y,
                                 ARROW_WIDTH * self.scale, ARROW_HEIGHT * self.scale)
