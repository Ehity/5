"""Сканер подписок: пайплайн «выписка -> подписки -> письма -> экономия».

Запуск:
    python main.py data/demo_statement.csv
    python main.py data/demo_statement.csv --cancel netflix ivi
    python main.py data/demo_statement.csv --interactive
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd  # noqa: E402

from src.clustering import DescriptionClusterer  # noqa: E402
from src.llm_agent import generate_unsubscribe_letter  # noqa: E402
from src.periodicity import Subscription, detect_periodicity  # noqa: E402
from src.savings import compute_savings  # noqa: E402
from src.statement import load_statement  # noqa: E402


def scan_subscriptions(statement_path: str) -> list[Subscription]:
    print(f"== Загружаю выписку: {statement_path}")
    df = load_statement(statement_path)
    print(f"   транзакций-списаний: {len(df)} "
          f"({df['date'].min():%d.%m.%Y} — {df['date'].max():%d.%m.%Y})")

    print("== Кластеризую названия мерчантов (эмбеддинги + правила)...")
    clusterer = DescriptionClusterer().fit(df["description"].tolist())
    df["cluster"] = df["description"].map(clusterer.label_for)
    names = clusterer.cluster_names()

    print("== Ищу периодические списания...")
    subs: list[Subscription] = []
    for cid, variants in names.items():
        tx = df[df["cluster"] == cid]
        sub = detect_periodicity(tx, cid, DescriptionClusterer.cluster_title(variants), variants)
        if sub:
            subs.append(sub)

    subs.sort(key=lambda s: -s.monthly_cost)
    print(f"   найдено подписок: {len(subs)}\n")
    return subs


def print_subscriptions(subs: list[Subscription]) -> None:
    if not subs:
        print("Подписок не найдено.")
        return
    table = pd.DataFrame([s.to_dict() for s in subs])
    print(table.to_string(index=False))
    monthly = sum(s.monthly_cost for s in subs)
    print(f"\nИтого по всем подпискам: {monthly:.2f} руб./мес ({monthly * 12:.2f} руб./год)")


def pick_interactively(subs: list[Subscription]) -> list[str]:
    print("\nОтметьте подписки, от которых хотите отказаться (номера через запятую, Enter — все):")
    for i, s in enumerate(subs, 1):
        print(f"  {i}. {s.title} — {s.monthly_cost:.2f} руб./мес")
    try:
        raw = input("> ").strip()
    except EOFError:  # stdin закрыт (запуск без консольного ввода)
        print("\nВвод недоступен — выбор не сделан.")
        return []
    if not raw:
        return [s.title for s in subs]
    chosen = []
    for part in raw.replace(" ", "").split(","):
        if part.isdigit() and 1 <= int(part) <= len(subs):
            chosen.append(subs[int(part) - 1].title)
    return chosen


def main() -> None:
    ap = argparse.ArgumentParser(description="Сканер подписок по банковской выписке")
    ap.add_argument("statement", help="путь к CSV-выписке")
    ap.add_argument("--cancel", nargs="*", default=[],
                    help="названия подписок для отмены (подстроки)")
    ap.add_argument("--interactive", action="store_true",
                    help="выбрать подписки для отмены интерактивно")
    args = ap.parse_args()

    subs = scan_subscriptions(args.statement)
    print_subscriptions(subs)

    to_cancel = pick_interactively(subs) if args.interactive else args.cancel
    if not to_cancel:
        print("\nДля расчёта экономии укажите --cancel <названия> или --interactive")
        return

    report = compute_savings(subs, to_cancel)
    print(f"\n== Отказываемся от {len(report.cancelled)} подписок: "
          f"экономия {report.yearly_total:,.2f} руб./год".replace(",", " "))

    print("\n== Готовлю письма для отписки...")
    for s in report.cancelled:
        letter, source = generate_unsubscribe_letter(s)
        tag = "LLM" if source == "llm" else "шаблон"
        print(f"\n----- {s.title} (источник: {tag}) -----")
        print(letter)
    print("\nГотово.")


if __name__ == "__main__":
    main()
