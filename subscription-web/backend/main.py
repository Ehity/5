"""Сбер.Сканер Подписок — FastAPI backend.

Эндпоинты:
    GET  /api/health           — статус
    GET  /api/subscriptions    — анализ или демо-данные (fallback mock)
    POST /api/upload           — загрузка CSV-выписки, анализ
    POST /api/generate-letter  — текст заявления на отмену автопродления
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from analyzer import demo_payload, detect_subscriptions, monthly_expense_series, parse_csv

app = FastAPI(title="Сбер.Сканер Подписок API", version="1.0.0")

# Раздача собранного фронтенда (frontend/dist), если он собран
_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # для хакатонного MVP
    allow_methods=["*"],
    allow_headers=["*"],
)

# Состояние анализа в памяти процесса (для MVP достаточно)
_state: dict | None = None


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "Сбер.Сканер Подписок", "today": date.today().isoformat()}


@app.get("/api/subscriptions")
def get_subscriptions() -> dict:
    """Анализ загруженной выписки; если её нет — демо-данные (fallback mock)."""
    if _state is not None:
        return _state
    return demo_payload()


@app.post("/api/upload")
async def upload_statement(file: UploadFile = File(...)) -> dict:
    """Принимает CSV-выписку, ищет подписки и сохраняет результат анализа."""
    global _state
    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Файл пуст")

    try:
        txs = parse_csv(content)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e

    subs = detect_subscriptions(txs)
    if not subs:
        # Fallback: файл не дал подписок — показываем демо, UI остаётся презентабельным
        payload = demo_payload()
        payload["message"] = ("В выписке не найдено регулярных списаний "
                              f"({len(txs)} транзакций). Показаны демонстрационные данные")
        return payload

    _state = {
        "mock": False,
        "subscriptions": subs,
        "monthly": monthly_expense_series(subs),
        "total_monthly": round(sum(s["monthly_cost"] for s in subs), 2),
        "total_yearly": round(sum(s["yearly_cost"] for s in subs), 2),
        "message": f"Выписка «{file.filename}»: {len(txs)} транзакций, найдено подписок: {len(subs)}",
    }
    return _state


@app.post("/api/reset")
def reset() -> dict:
    """Сбрасывает загруженную выписку, возвращает сервис в демо-режим."""
    global _state
    _state = None
    return {"status": "reset"}


class LetterRequest(BaseModel):
    name: str
    amount: float | None = None
    period: str = "ежемесячно"


LETTER_TEMPLATE = """Кому: Служба поддержки «{name}»
Тема: Отказ от автопродления подписки и прекращение списаний

Здравствуйте!

Я, пользователь сервиса «{name}», настоящим уведомляю об отказе от продления
подписки (услуги) с автопродлением{amount_line} и требую прекратить списание
денежных средств с моего банковского счёта.

В соответствии со ст. 32 Закона РФ «О защите прав потребителей» потребитель
вправе отказаться от исполнения договора об оказании услуг в любое время при
оплате фактически понесённых расходов исполнителя. В соответствии со ст. 782
ГК РФ заказчик вправе отказаться от исполнения договора возмездного оказания
услуг при условии оплаты исполнителю фактически понесённых им расходов.

Прошу:
1. Отключить автоматическое продление подписки «{name}».
2. Прекратить дальнейшие списания с моего счёта.
3. Вернуть оплату за неиспользованный период, если списание уже произведено.
4. Подтвердить отключение подписки ответным письмом в течение 10 дней
   (ст. 31 Закона РФ «О защите прав потребителей»).

Дата последнего списания: {last_line}
Дата обращения: {today}

С уважением,
Клиент сервиса «{name}»"""


@app.post("/api/generate-letter")
def generate_letter(req: LetterRequest) -> dict:
    """Готовит юридически корректный текст заявления на отмену подписки."""
    amount_line = ""
    if req.amount:
        amount_line = f" в размере {req.amount:,.2f} руб./мес".replace(",", " ")
    letter = LETTER_TEMPLATE.format(
        name=req.name,
        amount_line=amount_line,
        last_line=date.today().isoformat(),
        today=date.today().strftime("%d.%m.%Y"),
    )
    return {"letter": letter, "name": req.name}


# ---------------------------------------------------------------------------
# Раздача production-сборки фронтенда (один сервер на всё: http://127.0.0.1:8000)
# Монтируется последним, чтобы не перехватывать /api-роуты.
# ---------------------------------------------------------------------------
if _DIST.exists():
    app.mount("/assets", StaticFiles(directory=_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(_DIST / "index.html")

    @app.get("/{path:path}", include_in_schema=False)
    def spa_fallback(path: str) -> FileResponse:
        """SPA-fallback: любые не-/api пути отдают index.html."""
        candidate = _DIST / path
        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(_DIST / "index.html")
