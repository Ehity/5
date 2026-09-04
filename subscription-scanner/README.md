# Сканер подписок — Кейс 4 (Сбер)

AI-сервис, который находит подписки в банковской выписке за 6 месяцев и помогает
отказаться от ненужных: ищет повторяющиеся списания, кластеризует названия
мерчантов эмбеддингами (SentenceTransformers), детектирует периодичность,
генерирует LLM-письмо для отписки и считает годовую экономию.

## Архитектура пайплайна

```
CSV-выписка → statement.py (нормализация)
            → clustering.py (эмбеддинги MiniLM + правила → кластеры-подписки)
            → periodicity.py (детект ежемесячных/ежегодных списаний)
            → savings.py (экономия за год)
            → llm_agent.py (письмо на отписку; OpenAI-совместимый API или шаблон)
```

## Установка

```bash
python -m pip install torch --index-url https://download.pytorch.org/whl/cpu
python -m pip install -r requirements.txt
```

Первый запуск скачает модель `paraphrase-multilingual-MiniLM-L12-v2` (~470 МБ).

## Запуск в один клик

Двойной клик по **`run_scanner.bat`** (или по ярлыку «Сканер подписок» на рабочем
столе) — запускает сканер на демо-выписке в интерактивном режиме: покажет
найденные подписки и спросит, от каких отказаться.

- Ярлык создаётся скриптом `create_shortcut.ps1` (иконка — `icon.ico`,
  перегенерировать: `python make_icon.py`).

## Запуск на демо-данных

```bash
python data/generate_demo_data.py          # создаст data/demo_statement.csv
python main.py data/demo_statement.csv --cancel netflix ivi
```

Опции:
- `--cancel netflix ivi` — подписки к отмене (подстроки, регистр не важен);
- `--interactive` — выбрать подписки номерами в терминале.

## LLM-агент (опционально)

Без ключа письмо генерируется шаблоном. Для LLM задайте переменные окружения:

```bash
set LLM_API_KEY=...
set LLM_BASE_URL=https://api.openai.com/v1   # или GigaChat-эндпоинт
set LLM_MODEL=gpt-4o-mini
```

## Тесты

```bash
python -m pytest tests/ -v
```
