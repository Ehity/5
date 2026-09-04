import { useCallback, useEffect, useReducer } from 'react'
import {
    GRID_SIZE,
    INITIAL_DIRECTION,
    INITIAL_SNAKE,
    INITIAL_SPEED,
    KEY_DIRECTIONS,
    MIN_SPEED,
    SPEED_STEP,
} from '../constants'

/**
 * Возвращает случайную свободную клетку для еды.
 * Если всё поле занято змейкой — возвращает null (условие победы).
 */
function spawnFood(snake) {
    const occupied = new Set(snake.map(({ x, y }) => `${x},${y}`))
    const freeCells = []
    for (let x = 0; x < GRID_SIZE; x += 1) {
        for (let y = 0; y < GRID_SIZE; y += 1) {
            if (!occupied.has(`${x},${y}`)) {
                freeCells.push({ x, y })
            }
        }
    }
    if (freeCells.length === 0) return null
    return freeCells[Math.floor(Math.random() * freeCells.length)]
}

function createInitialState(status = 'idle') {
    return {
        status, // 'idle' | 'running' | 'over' | 'won'
        snake: INITIAL_SNAKE,
        direction: INITIAL_DIRECTION,
        directionQueue: [], // буфер нажатий между тиками
        food: spawnFood(INITIAL_SNAKE),
        score: 0,
        speed: INITIAL_SPEED,
    }
}

/**
 * Чистый редьюсер игрового состояния.
 * Все правила игры собраны здесь: движение, поедание еды,
 * рост змейки, подсчёт очков и проверки столкновений.
 */
function reducer(state, action) {
    switch (action.type) {
        case 'START':
            return createInitialState('running')

        case 'QUEUE_DIRECTION': {
            if (state.status !== 'running') return state

            // Сравниваем с последним запрошенным направлением (или текущим),
            // чтобы быстрые двойные нажатия не развернули змейку на 180°.
            const reference =
                state.directionQueue[state.directionQueue.length - 1] ??
                state.direction
            const { x, y } = action.direction
            const isReverse = x === -reference.x && y === -reference.y
            const isSame = x === reference.x && y === reference.y
            if (isReverse || isSame) return state

            // Храним не более трёх отложенных поворотов
            return {
                ...state,
                directionQueue: [...state.directionQueue, action.direction].slice(-3),
            }
        }

        case 'TICK': {
            if (state.status !== 'running') return state

            // Достаём из очереди первое допустимое направление
            let direction = state.direction
            const queue = [...state.directionQueue]
            while (queue.length > 0) {
                const candidate = queue.shift()
                const isReverse =
                    candidate.x === -direction.x && candidate.y === -direction.y
                const isSame =
                    candidate.x === direction.x && candidate.y === direction.y
                if (!isReverse && !isSame) {
                    direction = candidate
                    break
                }
            }

            const [head] = state.snake
            const newHead = { x: head.x + direction.x, y: head.y + direction.y }

            // Столкновение со стеной — игра окончена
            const hitWall =
                newHead.x < 0 ||
                newHead.y < 0 ||
                newHead.x >= GRID_SIZE ||
                newHead.y >= GRID_SIZE
            if (hitWall) {
                return { ...state, status: 'over', direction, directionQueue: [] }
            }

            // Если еда съедена — змейка растёт (хвост остаётся на месте),
            // иначе хвост освобождает клетку, и в неё можно безопасно двигаться.
            const willEat =
                state.food !== null &&
                newHead.x === state.food.x &&
                newHead.y === state.food.y
            const body = willEat ? state.snake : state.snake.slice(0, -1)

            // Столкновение с собственным телом — игра окончена
            const hitSelf = body.some(
                ({ x, y }) => x === newHead.x && y === newHead.y,
            )
            if (hitSelf) {
                return { ...state, status: 'over', direction, directionQueue: [] }
            }

            const snake = [newHead, ...body]
            const nextFood = willEat ? spawnFood(snake) : state.food

            return {
                ...state,
                direction,
                directionQueue: queue,
                snake,
                food: nextFood,
                score: willEat ? state.score + 1 : state.score,
                speed: willEat
                    ? Math.max(MIN_SPEED, state.speed - SPEED_STEP)
                    : state.speed,
                status: nextFood === null ? 'won' : state.status,
            }
        }

        default:
            return state
    }
}

/**
 * Пользовательский хук, инкапсулирующий всю логику «Змейки»:
 * состояние игры, игровой цикл и управление с клавиатуры.
 */
export function useSnakeGame() {
    const [state, dispatch] = useReducer(reducer, undefined, createInitialState)

    const start = useCallback(() => dispatch({ type: 'START' }), [])

    const turn = useCallback(
        (direction) => dispatch({ type: 'QUEUE_DIRECTION', direction }),
        [],
    )

    // Игровой цикл: каждые state.speed мс выполняется один шаг змейки.
    // Эффект перезапускается при смене статуса или ускорении игры.
    useEffect(() => {
        if (state.status !== 'running') return undefined
        const timerId = setInterval(() => dispatch({ type: 'TICK' }), state.speed)
        return () => clearInterval(timerId)
    }, [state.status, state.speed])

    // Управление с клавиатуры: стрелки / WASD — поворот,
    // Enter или пробел — старт и рестарт после проигрыша.
    useEffect(() => {
        const handleKeyDown = (event) => {
            const direction = KEY_DIRECTIONS[event.code]
            if (direction) {
                event.preventDefault()
                turn(direction)
                return
            }
            if (
                event.code === 'Enter' ||
                event.code === 'NumpadEnter' ||
                event.code === 'Space'
            ) {
                event.preventDefault()
                if (state.status !== 'running') start()
            }
        }

        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [turn, start, state.status])

    return { ...state, start }
}