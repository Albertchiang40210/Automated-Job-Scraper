import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from ai_matcher import fallback_score, parse_response
from discord_notifier import build_embeds
from scrapers.scraper_104 import is_relevant
from utils import dedupe_jobs


def test_fallback_no_substring_false_positive():
    assert fallback_score("please send email to maintain", ["ai"])["score"] == 60


def test_fallback_python_junior():
    assert fallback_score("Python Junior developer", ["python"])["score"] == 95


def test_parse_fenced_json():
    assert parse_response('```json\n{"score": 88, "reason": "ok"}\n```') == {"score": 88, "reason": "ok"}


def test_parse_clamps_score():
    assert parse_response('{"score": 150}')["score"] == 100


def test_parse_invalid():
    with pytest.raises(ValueError):
        parse_response("not json")


def test_dedupe():
    jobs = [{"link": "a?x=1"}, {"link": "a?x=2"}, {"link": "b"}]
    assert len(dedupe_jobs(jobs)) == 2


def test_embed_truncation():
    e = build_embeds([{"platform": "x", "title": "t", "reason": "r" * 9000, "score": 90}])
    assert len(e[0]["description"]) <= 4000


def test_relevance_filter():
    assert is_relevant("AI Engineer", "AI Engineer (內湖)", "")
    assert not is_relevant("AI Engineer", "平面視覺設計師", "設計 Photoshop")
    assert is_relevant("Python", "後端工程師", "熟悉 python")


def test_fallback_custom_keywords():
    assert fallback_score("徵行政人員", ["行政"])["score"] == 80
    assert fallback_score("徵工程師", ["行政"])["score"] == 60


def test_fallback_disabled_without_keywords():
    from ai_matcher import _fallback
    assert _fallback("python", None)["error"] is True


def test_fallback_levels():
    assert fallback_score("資深行政主管", ["行政"], level="senior")["score"] == 95
    assert fallback_score("資深行政主管", ["行政"], level="junior")["score"] == 70
    assert fallback_score("行政助理 無經驗可", ["行政"], level="senior")["score"] == 70
