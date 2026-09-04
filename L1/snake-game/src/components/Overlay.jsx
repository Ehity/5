/**
 * Полупрозрачный оверлей поверх игрового поля.
 * Используется для стартового экрана, экрана «Игра окончена» и победы.
 */
export default function Overlay({ visible, title, subtitle, buttonText, onButtonClick }) {
    if (!visible) return null

    return (
        <div className="overlay">
            <div className="overlay-card">
                <h2 className="overlay-title">{title}</h2>
                {subtitle && <p className="overlay-subtitle">{subtitle}</p>}
                <button type="button" className="overlay-button" onClick={onButtonClick}>
                    {buttonText}
                </button>
            </div>
        </div>
    )
}