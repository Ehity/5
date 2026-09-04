# -*- coding: utf-8 -*-
"""Классический Тетрис на pygame.

Управление:
    <-/->  — движение влево/вправо
    Вниз   — ускоренное падение (soft drop)
    Пробел — мгновенное падение (hard drop)
    Вверх / Z — поворот по/против часовой стрелки
    P      — пауза
    R      — рестарт
    Esc    — выход
"""

import random
import sys

import pygame

# ---------------------------------------------------------------- константы --
CELL = 30                      # размер клетки, пикселей
COLS, ROWS = 10, 20            # размер поля в клетках
HUD = 220                      # ширина панели справа
PADDING = 20
WIDTH = COLS * CELL + HUD + PADDING * 2
HEIGHT = ROWS * CELL + PADDING * 2
FPS = 60

BOARD_X = PADDING
BOARD_Y = PADDING

# Задержки падения: начальный интервал и ускорение с уровнем
BASE_FALL_MS = 800
MIN_FALL_MS = 80
FALL_STEP = 60                 # ускорение за уровень
SOFT_DROP_MS = 40

SCORES = {1: 100, 2: 300, 3: 500, 4: 800}   # за 1/2/3/4 линии
LINES_PER_LEVEL = 10

BG = (18, 18, 26)
GRID = (45, 45, 60)
BORDER = (90, 90, 120)
TEXT = (230, 230, 240)
DIM = (150, 150, 170)

# -------------------------------------------------------------- фигуры ------
# Каждая фигура задана списком поворотов (0°, 90°, 180°, 270°).
SHAPES = {
    "I": (
        ((0, 0, 0, 0), (1, 1, 1, 1), (0, 0, 0, 0), (0, 0, 0, 0)),
        ((0, 0, 1, 0), (0, 0, 1, 0), (0, 0, 1, 0), (0, 0, 1, 0)),
        ((0, 0, 0, 0), (0, 0, 0, 0), (1, 1, 1, 1), (0, 0, 0, 0)),
        ((0, 1, 0, 0), (0, 1, 0, 0), (0, 1, 0, 0), (0, 1, 0, 0)),
    ),
    "J": (
        ((1, 0, 0), (1, 1, 1), (0, 0, 0)),
        ((0, 1, 1), (0, 1, 0), (0, 1, 0)),
        ((0, 0, 0), (1, 1, 1), (0, 0, 1)),
        ((0, 1, 0), (0, 1, 0), (1, 1, 0)),
    ),
    "L": (
        ((0, 0, 1), (1, 1, 1), (0, 0, 0)),
        ((0, 1, 0), (0, 1, 0), (0, 1, 1)),
        ((0, 0, 0), (1, 1, 1), (1, 0, 0)),
        ((1, 1, 0), (0, 1, 0), (0, 1, 0)),
    ),
    "O": (
        ((1, 1), (1, 1)),
        ((1, 1), (1, 1)),
        ((1, 1), (1, 1)),
        ((1, 1), (1, 1)),
    ),
    "S": (
        ((0, 1, 1), (1, 1, 0), (0, 0, 0)),
        ((0, 1, 0), (0, 1, 1), (0, 0, 1)),
        ((0, 0, 0), (0, 1, 1), (1, 1, 0)),
        ((1, 0, 0), (1, 1, 0), (0, 1, 0)),
    ),
    "T": (
        ((0, 1, 0), (1, 1, 1), (0, 0, 0)),
        ((0, 1, 0), (0, 1, 1), (0, 1, 0)),
        ((0, 0, 0), (1, 1, 1), (0, 1, 0)),
        ((0, 1, 0), (1, 1, 0), (0, 1, 0)),
    ),
    "Z": (
        ((1, 1, 0), (0, 1, 1), (0, 0, 0)),
        ((0, 0, 1), (0, 1, 1), (0, 1, 0)),
        ((0, 0, 0), (1, 1, 0), (0, 1, 1)),
        ((0, 1, 0), (1, 1, 0), (1, 0, 0)),
    ),
}

COLORS = {
    "I": (0, 200, 220),
    "J": (60, 90, 230),
    "L": (235, 150, 40),
    "O": (235, 210, 40),
    "S": (80, 210, 90),
    "T": (180, 70, 220),
    "Z": (230, 70, 90),
}

GHOST_ALPHA = 60

class Piece:
    """Падающая фигура."""

    def __init__(self, kind: str, x: int = 0, y: int = 0, rot: int = 0):
        self.kind = kind
        self.x = x
        self.y = y
        self.rot = rot % 4

    @property
    def matrix(self):
        return SHAPES[self.kind][self.rot]

    def cells(self):
        """Координаты занятых клеток (cx, cy) в поле."""
        m = self.matrix
        for r, row in enumerate(m):
            for c, v in enumerate(row):
                if v:
                    yield self.x + c, self.y + r

    def rotated(self, dr: int) -> "Piece":
        return Piece(self.kind, self.x, self.y, (self.rot + dr) % 4)

    def moved(self, dx: int, dy: int) -> "Piece":
        return Piece(self.kind, self.x + dx, self.y + dy, self.rot)


class Game:
    """Игровая логика тетриса."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.next_kind = self._draw_from_bag()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        self.soft_dropping = False
        self.fall_ms = 0
        self.fall_interval = BASE_FALL_MS
        self.spawn()

    def _draw_from_bag(self) -> str:
        """Классический «мешок» 7 фигур: перемешанная пачка без повторов."""
        if not self.bag:
            self.bag = list(SHAPES)
            random.shuffle(self.bag)
        return self.bag.pop()

    # ---------------------------------------------------------- коллизии ---
    def collides(self, piece: Piece) -> bool:
        for cx, cy in piece.cells():
            if cx < 0 or cx >= COLS or cy >= ROWS:
                return True
            if cy >= 0 and self.board[cy][cx] is not None:
                return True
        return False

    # ------------------------------------------------------------ спавн ----
    def spawn(self):
        width = len(SHAPES[self.next_kind][0][0])
        self.current = Piece(self.next_kind, x=(COLS - width) // 2, y=-1)
        self.next_kind = self._draw_from_bag()
        self.fall_ms = 0
        if self.collides(self.current):
            self.game_over = True

    # ------------------------------------------------------- призрачная ----
    def ghost(self) -> Piece:
        p = self.current
        while not self.collides(p.moved(0, 1)):
            p = p.moved(0, 1)
        return p

    # ------------------------------------------------------------ ввод -----
    def try_move(self, dx: int, dy: int) -> bool:
        moved = self.current.moved(dx, dy)
        if not self.collides(moved):
            self.current = moved
            return True
        return False

    def try_rotate(self, dr: int) -> bool:
        rotated = self.current.rotated(dr)
        if not self.collides(rotated):
            self.current = rotated
            return True
        # простой wall kick: попытка сдвига в стороны и вверх
        for dx, dy in ((-1, 0), (1, 0), (0, -1), (-2, 0), (2, 0)):
            kicked = Piece(rotated.kind, rotated.x + dx, rotated.y + dy, rotated.rot)
            if not self.collides(kicked):
                self.current = kicked
                return True
        return False

    def hard_drop(self):
        dist = 0
        while not self.collides(self.current.moved(0, 1)):
            self.current = self.current.moved(0, 1)
            dist += 1
        self.score += dist * 2
        self.lock()

    # ------------------------------------------------------ фиксация -------
    def lock(self):
        for cx, cy in self.current.cells():
            if 0 <= cy < ROWS:
                self.board[cy][cx] = self.current.kind
        self.clear_lines()
        if not self.game_over:
            self.spawn()

    def clear_lines(self):
        full = [r for r in range(ROWS) if all(self.board[r])]
        if not full:
            return
        for r in full:
            del self.board[r]
            self.board.insert(0, [None] * COLS)
        self.lines += len(full)
        self.score += SCORES[len(full)] * self.level
        new_level = self.lines // LINES_PER_LEVEL + 1
        if new_level != self.level:
            self.level = new_level
            self.fall_interval = max(MIN_FALL_MS, BASE_FALL_MS - (self.level - 1) * FALL_STEP)

    # ---------------------------------------------------------- тик игры ---
    def update(self, dt_ms: int):
        if self.game_over or self.paused:
            return
        interval = SOFT_DROP_MS if self.soft_dropping else self.fall_interval
        self.fall_ms += dt_ms
        while self.fall_ms >= interval:
            self.fall_ms -= interval
            if not self.try_move(0, 1):
                self.lock()
                return


# --------------------------------------------------------------- отрисовка --
def draw_cell(surface, x, y, color, ghost=False):
    rect = pygame.Rect(x, y, CELL, CELL)
    if ghost:
        pygame.draw.rect(surface, color, rect, border_radius=4)
        veil = pygame.Surface((CELL, CELL), pygame.SRCALPHA)
        veil.fill((BG[0], BG[1], BG[2], 255 - GHOST_ALPHA))
        surface.blit(veil, rect)
    else:
        pygame.draw.rect(surface, color, rect, border_radius=4)
        light = tuple(min(255, ch + 60) for ch in color)
        pygame.draw.rect(surface, light, rect.inflate(-6, -6), border_radius=3)
    pygame.draw.rect(surface, BORDER, rect, 1, border_radius=4)


def draw_board(surface, game: Game, fonts):
    area = pygame.Rect(BOARD_X, BOARD_Y, COLS * CELL, ROWS * CELL)
    pygame.draw.rect(surface, (8, 8, 12), area)
    for c in range(COLS + 1):
        pygame.draw.line(surface, GRID, (area.x + c * CELL, area.y),
                         (area.x + c * CELL, area.bottom))
    for r in range(ROWS + 1):
        pygame.draw.line(surface, GRID, (area.x, area.y + r * CELL),
                         (area.right, area.y + r * CELL))

    # осевшие блоки
    for r in range(ROWS):
        for c in range(COLS):
            kind = game.board[r][c]
            if kind:
                draw_cell(surface, area.x + c * CELL, area.y + r * CELL, COLORS[kind])

    if not game.game_over:
        # призрак — место приземления
        g = game.ghost()
        for cx, cy in g.cells():
            if cy >= 0:
                draw_cell(surface, area.x + cx * CELL, area.y + cy * CELL,
                          COLORS[g.kind], ghost=True)
        # текущая фигура
        for cx, cy in game.current.cells():
            if cy >= 0:
                draw_cell(surface, area.x + cx * CELL, area.y + cy * CELL,
                          COLORS[game.current.kind])

    pygame.draw.rect(surface, BORDER, area, 2)

    if game.paused:
        overlay(surface, area, ("ПАУЗА",), fonts, DIM)
    elif game.game_over:
        overlay(surface, area, ("ИГРА", "ОКОНЧЕНА"), fonts, (230, 80, 90))


def overlay(surface, area, lines, fonts, color):
    veil = pygame.Surface(area.size, pygame.SRCALPHA)
    veil.fill((0, 0, 0, 170))
    surface.blit(veil, area.topleft)
    font = fonts["big"]
    total = len(lines) * font.get_height()
    for i, line in enumerate(lines):
        img = font.render(line, True, color)
        cy = area.centery - total // 2 + i * font.get_height() + font.get_height() // 2
        surface.blit(img, img.get_rect(center=(area.centerx, cy)))


def draw_next(surface, kind, x, y, font):
    title = font.render("СЛЕДУЮЩАЯ", True, DIM)
    surface.blit(title, (x, y))
    box_y = y + 30
    box = pygame.Rect(x, box_y, 4 * CELL + 10, 3 * CELL + 10)
    pygame.draw.rect(surface, (8, 8, 12), box)
    pygame.draw.rect(surface, BORDER, box, 1)
    m = SHAPES[kind][0]
    size = len(m[0])
    off_x = box.x + (box.w - size * CELL) // 2
    off_y = box.y + (box.h - len(m) * CELL) // 2
    for r, row in enumerate(m):
        for c, v in enumerate(row):
            if v:
                draw_cell(surface, off_x + c * CELL, off_y + r * CELL, COLORS[kind])


def draw_hud(surface, game: Game, fonts):
    x = BOARD_X + COLS * CELL + PADDING + 10
    y = BOARD_Y

    def stat(label, value, dy):
        lab = fonts["small"].render(label, True, DIM)
        val = fonts["medium"].render(str(value), True, TEXT)
        surface.blit(lab, (x, y + dy))
        surface.blit(val, (x, y + dy + 20))

    draw_next(surface, game.next_kind, x, y, fonts["small"])
    base = 3 * CELL + 60
    stat("СЧЁТ", game.score, base)
    stat("УРОВЕНЬ", game.level, base + 75)
    stat("ЛИНИИ", game.lines, base + 150)

    hint_y = base + 240
    hints = [
        "<- ->  движение",
        "Вверх/Z поворот",
        "Вниз   ускорить",
        "Пробел сброс",
        "P пауза  R заново",
        "Esc    выход",
    ]
    for i, h in enumerate(hints):
        img = fonts["tiny"].render(h, True, DIM)
        surface.blit(img, (x, y + hint_y + i * 20))


# ------------------------------------------------------------------- main ---
def main():
    pygame.init()
    pygame.display.set_caption("Тетрис")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    fonts = {
        "tiny": pygame.font.SysFont("consolas", 14),
        "small": pygame.font.SysFont("consolas", 16, bold=True),
        "medium": pygame.font.SysFont("consolas", 26, bold=True),
        "big": pygame.font.SysFont("consolas", 34, bold=True),
    }

    game = Game()
    running = True
    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_r:
                    game.reset()
                elif game.game_over:
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        game.reset()
                elif event.key == pygame.K_p:
                    game.paused = not game.paused
                elif not game.paused:
                    if event.key in (pygame.K_LEFT, pygame.K_a):
                        game.try_move(-1, 0)
                    elif event.key in (pygame.K_RIGHT, pygame.K_d):
                        game.try_move(1, 0)
                    elif event.key in (pygame.K_UP, pygame.K_w):
                        game.try_rotate(1)
                    elif event.key == pygame.K_z:
                        game.try_rotate(-1)
                    elif event.key == pygame.K_SPACE:
                        game.hard_drop()
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        game.soft_dropping = True
            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_DOWN, pygame.K_s):
                    game.soft_dropping = False

        game.update(dt)

        screen.fill(BG)
        draw_board(screen, game, fonts)
        draw_hud(screen, game, fonts)
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()


