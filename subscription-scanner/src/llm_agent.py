"""LLM-агент: персонализированное письмо для отписки от сервиса.

Работает с любым OpenAI-совместимым API (в т.ч. GigaChat от Сбера):
переменные окружения LLM_API_KEY, LLM_BASE_URL, LLM_MODEL.
Без ключа используется детерминированный шаблон (fallback), чтобы
прототип работал на демо без внешних сервисов.
"""

from __future__ import annotations

import os

from .periodicity import Subscription

_SYSTEM_PROMPT = (
    "Ты — вежливый ассистент, который помогает клиенту отказаться от платной подписки. "
    "Пиши кратко, деловым тоном, на русском языке. Верни только текст письма: "
    "тема и тело, без markdown-разметки."
)


def _fallback_letter(sub: Subscription) -> str:
    period = "ежемесячную" if sub.period == "monthly" else "ежегодную"
    sum_str = f"{sub.median_amount:,.2f}".replace(",", " ")
    return (
        f"Тема: Отмена {period} подписки {sub.title}\n\n"
        f"Здравствуйте!\n\n"
        f"Прошу отключить {period} подписку «{sub.title}» с {sub.last_date:%d.%m.%Y} "
        f"и прекратить дальнейшие списания в размере {sum_str} руб.\n\n"
        f"Если подписка была подключена ошибочно, прошу вернуть средства за "
        f"последний оплаченный период.\n\n"
        f"Прошу подтвердить отмену письмом на этот адрес.\n\n"
        f"С уважением,\nКлиент"
    )


def generate_unsubscribe_letter(sub: Subscription) -> tuple[str, str]:
    """Возвращает (письмо, источник), источник = 'llm' | 'template'."""
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        return _fallback_letter(sub), "template"

    try:
        from openai import OpenAI

        client = OpenAI(
            api_key=api_key,
            base_url=os.environ.get("LLM_BASE_URL", "https://api.openai.com/v1"),
        )
        user_prompt = (
            f"Напиши письмо на отписку от сервиса.\n"
            f"Сервис: {sub.title}\n"
            f"Варианты названия в выписке: {', '.join(sub.variants[:3])}\n"
            f"Тариф: {'ежемесячный' if sub.period == 'monthly' else 'ежегодный'}, "
            f"{sub.median_amount:.2f} руб.\n"
            f"Последнее списание: {sub.last_date:%d.%m.%Y}\n"
            f"Тон: вежливый, краткий. Попроси отключить подписку, прекратить списания, "
            f"подтвердить отмену и вернуть средства за последний период, если он не использовался."
        )
        resp = client.chat.completions.create(
            model=os.environ.get("LLM_MODEL", "gpt-4o-mini"),
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.4,
        )
        return resp.choices[0].message.content.strip(), "llm"
    except Exception as e:
        print(f"[llm] API недоступен ({e.__class__.__name__}: {e}); использую шаблон")
        return _fallback_letter(sub), "template"
