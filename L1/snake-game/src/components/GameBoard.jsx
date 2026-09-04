import { GRID_SIZE } from '../constants'

/**
 * Игровое поле — сетка GRID_SIZE x GRID_SIZE.
 * Отрисовывает змейку (голова подсвечена) и еду.
 */
export default function GameBoard({ snake, food }) {
    const head = snake[0]
    const snakeCells = new Set(snake.map(({ x, y }) => `${x},${y}`))
    const foodKey = food ? `${food.x},${food.y}` : null

    const cells = []
    for (let y = 0; y < GRID_SIZE; y += 1) {
        for (let x = 0; x < GRID_SIZE; x += 1) {
            const key = `${x},${y}`
            let className = 'cell'
            if (key === foodKey) {
                className += ' cell--food'
            } else if (snakeCells.has(key)) {
                className +=
                    key === `${head.x},${head.y}` ? ' cell--head' : ' cell--snake'
            }
            cells.push(<div key={key} className={className} />)
        }
    }

    return <div className="board">{cells}</div>
}