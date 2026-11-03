#!/usr/bin/env python3
"""Sentiment scorer — lexicon-based, with Hinglish support.

Two scorers, never blended:
1. English financial lexicon (Loughran-McDonald style)
2. Hinglish code-mixed lexicon (Hindi-English mix common in Indian markets)

Each returns -1.0 to +1.0. The strategy uses them as separate signals.
"""

# Simplified English financial lexicon (positive/negative word lists)
EN_POSITIVE = {"surge", "rally", "breakout", "upgrade", "beat", "growth", "profit", "gain"}
EN_NEGATIVE = {"crash", "downgrade", "miss", "loss", "fall", "drop", "concern", "risk"}

# Hinglish lexicon — Hindi words in Latin script common in market chatter
HINGLISH_POSITIVE = {"badha", "munafa", "tej", "upar", "bull", "badhiya"}
HINGLISH_NEGATIVE = {"gira", "nuksaan", "mandi", "neeche", "bear", "kharab"}


def score_english(text):
    words = set(text.lower().split())
    pos = len(words & EN_POSITIVE)
    neg = len(words & EN_NEGATIVE)
    total = pos + neg
    return (pos - neg) / total if total else 0.0


def score_hinglish(text):
    words = set(text.lower().split())
    pos = len(words & HINGLISH_POSITIVE)
    neg = len(words & HINGLISH_NEGATIVE)
    total = pos + neg
    return (pos - neg) / total if total else 0.0


def score(text):
    """Returns (english_score, hinglish_score) — never blended."""
    return score_english(text), score_hinglish(text)
