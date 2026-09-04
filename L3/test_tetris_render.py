# -*- coding: utf-8 -*-
"""Smoke-тест отрисовки: один кадр без реального окна."""
import os

os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import sys
sys.path.insert(0, r"c:\Python")

import pygame
import tetris as t

pygame.init()
screen = pygame.display.set_mode((t.WIDTH, t.HEIGHT))
fonts = {
    "tiny": pygame.font.SysFont("consolas", 14),
    "small": pygame.font.SysFont("consolas", 16, bold=True),
    "medium": pygame.font.SysFont("consolas", 26, bold=True),
    "big": pygame.font.SysFont("consolas", 34, bold=True),
}

game = t.Game()
screen.fill(t.BG)
t.draw_board(screen, game, fonts)
t.draw_hud(screen, game, fonts)
pygame.display.flip()

# кадры с паузой и game over
game.paused = True
t.draw_board(screen, game, fonts)
game.paused = False
game.game_over = True
t.draw_board(screen, game, fonts)
pygame.display.flip()

# полный main() при dummy-драйвере: выйти после первого кадра нельзя штатно,
# поэтому просто проверяем, что все константы окна согласованы
assert t.WIDTH == t.COLS * t.CELL + t.HUD + t.PADDING * 2
assert t.HEIGHT == t.ROWS * t.CELL + t.PADDING * 2
print("RENDER_SMOKE_OK")
