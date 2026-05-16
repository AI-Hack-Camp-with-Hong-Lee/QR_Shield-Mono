# -*- coding: utf-8 -*-
from app.ml.redirect import calculate_redirect_score


def test_short_url_and_domain_changed_scores():
    info = {
        "hop_count": 2,
        "is_short_url": True,
        "domain_changed": True,
        "suspicious_tld": False,
    }
    score, factors = calculate_redirect_score(info)

    types = {f["type"] for f in factors}
    assert score >= 45
    assert "short_url" in types
    assert "redirect" in types
    assert "domain_changed" in types


def test_excessive_redirect_adds_factor():
    info = {
        "hop_count": 4,
        "is_short_url": False,
        "domain_changed": False,
        "suspicious_tld": True,
    }
    score, factors = calculate_redirect_score(info)

    types = {f["type"] for f in factors}
    assert "excessive_redirect" in types
    assert "suspicious_tld" in types
    assert score >= 40
