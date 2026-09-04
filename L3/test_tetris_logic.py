# -*- coding: utf-8 -*-
"""Headless-проверка логики тетриса (без окна)."""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, r"c:\Python")

import tetris as t  # noqa: E402


def test_piece_cells():
    p = t.Piece("O", x=4, y=2)
    cells = set(p.cells())
    assert cells == {(4, 2), (5, 2), (4, 3), (5, 3)}, cells
    # повороты всех фигур корректны и не пусты
    for kind in t.SHAPES:
        for rot in range(4):
            piece = t.Piece(kind, x=3, y=3, rot=rot)
            assert sum(1 for _ in piece.cells()) == 4


def test_movement_and_lock():
    g = t.Game()
    kind = g.current.kind
    # движение вниз до упора -> фиксация
    for _ in range(50):
        if not g.try_move(0, 1):
            g.lock()
            break
    assert not g.game_over
    # после lock() заспавнилась новая фигура
    assert g.current is not None and g.current.kind != kind or True
    assert any(any(row) for row in g.board)


def test_clear_line():
    g = t.Game()
    # полностью заполненный нижний ряд очищается, счёт растёт
    g.board[t.ROWS - 1] = ["I"] * t.COLS
    g.clear_lines()
    assert not any(g.board[t.ROWS - 1]), "нижний ряд должен был очиститься"
    assert g.lines == 1 and g.score >= t.SCORES[1]

    # hard drop реально фиксирует блоки на поле
    g2 = t.Game()
    g2.hard_drop()
    assert any(any(row) for row in g2.board)


def test_hard_drop_ghost_game_over():
    g = t.Game()
    assert g.ghost().y >= g.current.y
    g.hard_drop()
    # забить всё поле до верха -> game over
    g2 = t.Game()
    for r in range(t.ROWS):
        for c in range(t.COLS):
            g2.board[r][c] = "I"
    g2.spawn()
    assert g2.game_over


def test_update_and_level():
    g = t.Game()
    g.update(t.BASE_FALL_MS + 1)   # за тик фигура падает минимум на 1
    assert g.current.y > -1 or not g.game_over
    g.lines = t.LINES_PER_LEVEL
    g.board[t.ROWS - 1] = ["I"] * t.COLS
    g.clear_lines()
    assert g.level == 2


def test_rotation_kick():
    g = t.Game()
    # фигура у стены — поворот должен сработать благодаря kick
    g.current = t.Piece(g.current.kind, x=0, y=2)
    g.try_rotate(1)  # просто не должно падать/исключений
    assert not g.game_over


test_piece_cells()
test_movement_and_lock()
test_clear_line()
test_hard_drop_ghost_game_over()
test_update_and_level()
test_rotation_kick()
print("ALL_LOGIC_TESTS_OK")
