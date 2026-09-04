"""Кластеризация названий транзакций: эмбеддинги (SentenceTransformers) + правила нормализации.

Объединяет варианты вроде «Netflix», «NFLX», «NETFLIX.COM 866-579-7172» в одну подписку.
"""

from __future__ import annotations

import re
from functools import lru_cache

import numpy as np

# Известные сокращения мерчантов -> каноничное имя
ABBREV_MAP = {
    "NFLX": "NETFLIX",
    "SPOT": "SPOTIFY",
    "SBOL": "СБЕРБОЛ",
}

_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
# Эмбеддинги — подтверждающий сигнал: на коротких названиях брендов косинус
# шумит («ЯНДЕКС ПЛЮС» ~ «ЯНДЕКС ТАКСИ» = 0.97), поэтому требуем ещё и
# лексическое пересечение токенов (Jaccard >= 0.5).
_SIM_THRESHOLD = 0.75
_JACCARD_THRESHOLD = 0.5


def normalize_description(desc: str) -> str:
    """Приводит название мерчанта к каноничной строке.

    Убирает цифры, телефоны, адреса сайтов, гео-метки, пунктуацию;
    раскрывает известные сокращения; приводит к верхнему регистру.
    """
    s = str(desc).upper()
    s = re.sub(r"HTTPS?://\S+|WWW\.\S+", " ", s)        # адреса сайтов
    s = re.sub(r"\S*\d\S*", " ", s)                     # токены с цифрами (телефоны, коды, филиалы)
    s = re.sub(r"\.[A-ZА-ЯЁ]{2,3}\b", " ", s)           # домены (.com, .ru)
    s = re.sub(r"\b(US|RU|GB|SG|LU|IE|NL)\b", " ", s)   # коды стран
    s = re.sub(r"[^A-ZА-ЯЁ ]+", " ", s)
    tokens = [ABBREV_MAP.get(t, t) for t in s.split() if len(t) >= 2]
    return " ".join(tokens).strip()


@lru_cache(maxsize=1)
def _get_embedder():
    from sentence_transformers import SentenceTransformer  # ленивый импорт

    return SentenceTransformer(_MODEL_NAME)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Эмбеддинги нормализованных названий (L2-нормализованные -> косинус = скалярное произведение)."""
    model = _get_embedder()
    return model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


class DescriptionClusterer:
    """Склеивает уникальные названия мерчантов в кластеры-подписки.

    Двухступенчато:
    1) правила: одинаковая нормализованная строка или вложенность токенов;
    2) эмбеддинги: косинусная близость нормализованных названий >= порога.
    """

    def fit(self, descriptions: list[str]) -> "DescriptionClusterer":
        self.descriptions = list(dict.fromkeys(d for d in descriptions if d))
        self.norm = [normalize_description(d) for d in self.descriptions]
        n = len(self.descriptions)
        parent = list(range(n))

        def find(i: int) -> int:
            while parent[i] != i:
                parent[i] = parent[parent[i]]
                i = parent[i]
            return i

        def union(i: int, j: int) -> None:
            ri, rj = find(i), find(j)
            if ri != rj:
                parent[max(ri, rj)] = min(ri, rj)

        # Правило 1: идентичные нормализованные строки
        by_norm: dict[str, int] = {}
        for i, norm in enumerate(self.norm):
            if norm in by_norm:
                union(i, by_norm[norm])
            else:
                by_norm[norm] = i

        # Правило 2: вложенность токенов («NETFLIX» в «NETFLIXCOM» уже склеено
        # нормализацией; здесь ловим «NETFLIX» в «NETFLIX MUSIC»)
        token_sets = [set(norm.split()) for norm in self.norm]
        for i in range(n):
            for j in range(i + 1, n):
                a, b = token_sets[i], token_sets[j]
                if not a or not b:
                    continue
                if a <= b or b <= a:  # «NETFLIX» ⊆ «NETFLIX MUSIC»
                    union(i, j)

        # Правило 3: эмбеддинги как подтверждающий сигнал
        if n > 1 and self._try_embeddings():
            embs = embed_texts(self.norm)  # type: ignore[arg-type]
            for i in range(n):
                for j in range(i + 1, n):
                    inter = len(token_sets[i] & token_sets[j])
                    union_size = len(token_sets[i] | token_sets[j])
                    if union_size and inter / union_size < _JACCARD_THRESHOLD:
                        continue  # нет лексической опоры — эмбеддингу не верим
                    sim = float(np.dot(embs[i], embs[j]))
                    if sim >= _SIM_THRESHOLD:
                        union(i, j)

        roots: dict[int, int] = {}
        self.labels_: list[int] = []
        for i in range(n):
            r = find(i)
            roots.setdefault(r, len(roots))
            self.labels_.append(roots[r])

        self.cluster_map_ = dict(zip(self.descriptions, self.labels_))
        return self

    def _try_embeddings(self) -> bool:
        try:
            _get_embedder()
            return True
        except Exception as e:  # модель не скачана / нет интернета
            print(f"[clusterer] эмбеддинги недоступны ({e.__class__.__name__}); "
                  f"использую только правила нормализации")
            return False

    def label_for(self, description: str) -> int:
        return self.cluster_map_[description]

    def cluster_names(self) -> dict[int, list[str]]:
        """{cluster_id: [варианты названий]}"""
        out: dict[int, list[str]] = {}
        for desc, label in self.cluster_map_.items():
            out.setdefault(label, []).append(desc)
        return out

    @staticmethod
    def cluster_title(variants: list[str]) -> str:
        """Человекочитаемое имя кластера — самое короткое каноничное название."""
        normed = sorted({normalize_description(v) for v in variants}, key=len)
        return normed[0] if normed else (variants[0] if variants else "UNKNOWN")
