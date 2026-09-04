import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.clustering import DescriptionClusterer, normalize_description


def test_normalize_strips_noise():
    assert normalize_description("NETFLIX.COM 866-579-7172 US") == "NETFLIX"
    assert normalize_description("NFLX* B8R2K3P4 866-579-7172") == "NETFLIX"
    assert normalize_description("Netflix") == "NETFLIX"


def test_netflix_variants_cluster_together():
    variants = ["NETFLIX.COM 866-579-7172 US", "NFLX* B8R2K3P4 866-579-7172",
                "Netflix", "ПЯТЕРОЧКА", "ЯНДЕКС.ПЛЮС", "ЯНДЕКС ТАКСИ"]
    c = DescriptionClusterer().fit(variants)
    labels = {v: c.label_for(v) for v in variants}
    # все варианты Netflix — один кластер
    nf = {labels["NETFLIX.COM 866-579-7172 US"], labels["NFLX* B8R2K3P4 866-579-7172"],
          labels["Netflix"]}
    assert len(nf) == 1
    # шум не попал в кластер Netflix
    assert labels["ПЯТЕРОЧКА"] not in nf
    # разные яндекс-сервисы не склеились в один кластер
    assert labels["ЯНДЕКС.ПЛЮС"] != labels["ЯНДЕКС ТАКСИ"]


def test_cluster_title_shortest_variant():
    title = DescriptionClusterer.cluster_title(
        ["NETFLIX.COM 866-579-7172 US", "Netflix"])
    assert title == "NETFLIX"
