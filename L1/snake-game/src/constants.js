// Размер игрового поля в клетках (поле квадратное: GRID_SIZE x GRID_SIZE)
export const GRID_SIZE = 20

// Начальная скорость игры — интервал между шагами змейки в миллисекундах
export const INITIAL_SPEED = 160

// Максимальная скорость (минимальный интервал) — игра ускоряется с ростом счёта
export const MIN_SPEED = 70

// Ускорение за каждую съеденную еду (мс, вычитается из интервала)
export const SPEED_STEP = 4

// Начальное положение змейки (голова первая, смотрит вправо)
export const INITIAL_SNAKE = [
    { x: 8, y: 10 },
    { x: 7, y: 10 },
    { x: 6, y: 10 },
]

// Начальное направление движения — вправо
export const INITIAL_DIRECTION = { x: 1, y: 0 }

// Соответствие клавиш (event.code) векторам направления.
// Используется event.code, поэтому WASD работает на любой раскладке клавиатуры.
export const KEY_DIRECTIONS = {
    ArrowUp: { x: 0, y: -1 },
    ArrowDown: { x: 0, y: 1 },
    ArrowLeft: { x: -1, y: 0 },
    ArrowRight: { x: 1, y: 0 },
    KeyW: { x: 0, y: -1 },
    KeyS: { x: 0, y: 1 },
    KeyA: { x: -1, y: 0 },
    KeyD: { x: 1, y: 0 },
}