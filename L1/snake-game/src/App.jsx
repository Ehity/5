import { useEffect, useState } from 'react'
import GameBoard from './components/GameBoard'
import Overlay from './components/Overlay'
import ScorePanel from './components/ScorePanel'
import { useSnakeGame } from './hooks/useSnakeGame'
import './App.css'

const BEST_SCORE_KEY = 'snake-best-score'

function loadBestScore() {
    const saved = Number(window.localStorage.getItem(BEST_SCORE_KEY))
    return Number.isFinite(saved) && saved > 0 ? saved : 0
}

/**
 * Корневой компонент игры «Змейка».
 * Связывает игровую логику (хук useSnakeGame) с UI-компонентами.
 */
export default function App() {
    const { status, snake, food, score, start } = useSnakeGame()
    const [bestScore, setBestScore] = useState(loadBestScore)

    // Обновляем рекорд и сохраняем его в localStorage
    useEffect(() => {
        if (score > bestScore) {
            setBestScore(score)
            window.localStorage.setItem(BEST_SCORE_KEY, String(score))
        }
    }, [score, bestScore])

    return (
        <main className="page">
            <h1 className="title">🐍 Змейка</h1>

            <ScorePanel score={score} best={bestScore} />

            <div className="board-wrap">
                <GameBoard snake={snake} food={food} />

                <Overlay
                    visible={status === 'idle'}
                    title="Готовы?"
                    subtitle="Собирайте еду, растите и не врезайтесь в стены и собственный хвост."
                    buttonText="Начать игру"
                    onButtonClick={start}
                />

                <Overlay
                    visible={status === 'over'}
                    title="Игра окончена"
                    subtitle={
                        score > 0
                            ? `Змейка врезалась. Ваш результат: ${score}`
                            : 'Змейка врезалась в стену или в себя.'
                    }
                    buttonText="Играть снова"
                    onButtonClick={start}
                />

                <Overlay
                    visible={status === 'won'}
                    title="Победа!"
                    subtitle="Вы заполнили змейкой всё поле. Невероятно!"
                    buttonText="Играть снова"
                    onButtonClick={start}
                />
            </div>

            <p className="hint">
                Стрелки / WASD — движение · Enter или пробел — старт и рестарт
            </p>
        </main>
    )
}