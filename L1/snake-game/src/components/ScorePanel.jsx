/**
 * Панель очков: текущий результат и рекорд (сохраняется в localStorage).
 */
export default function ScorePanel({ score, best }) {
    return (
        <div className="score-panel">
            <div className="score-item">
                <span className="score-label">Очки</span>
                <span className="score-value">{score}</span>
            </div>
            <div className="score-item">
                <span className="score-label">Рекорд</span>
                <span className="score-value">{best}</span>
            </div>
        </div>
    )
}