"""
Unit tests for pure computational functions in ml/hybrid_recommender.py.
No database or model fitting needed — tests the math directly.
"""

import numpy as np

from app.ml.hybrid_recommender import _normalize, _recency_score, WEIGHTS


class TestNormalize:
    def test_normalizes_to_zero_one_range(self):
        values = np.array([10.0, 20.0, 30.0])
        result = _normalize(values)
        assert result.min() == 0.0
        assert result.max() == 1.0

    def test_handles_identical_values(self):
        """All-identical input should return zeros, not divide by zero."""
        values = np.array([5.0, 5.0, 5.0])
        result = _normalize(values)
        assert np.all(result == 0.0)

    def test_preserves_relative_order(self):
        values = np.array([3.0, 1.0, 2.0])
        result = _normalize(values)
        assert result[1] < result[2] < result[0]


class TestRecencyScore:
    def test_none_release_date_returns_zero(self):
        assert _recency_score(None) == 0.0

    def test_invalid_format_returns_zero(self):
        assert _recency_score("not-a-date") == 0.0

    def test_today_scores_close_to_one(self):
        from datetime import date

        today_str = date.today().strftime("%Y-%m-%d")
        score = _recency_score(today_str)
        assert score > 0.99

    def test_old_content_scores_low(self):
        score = _recency_score("2000-01-01")
        assert score == 0.0

    def test_future_release_date_does_not_crash(self):
        """Upcoming content (future release) should not produce negative days_old issues."""
        from datetime import date, timedelta

        future_str = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
        score = _recency_score(future_str)
        assert score >= 0.0


class TestWeightsConfiguration:
    def test_weights_sum_to_one(self):
        """Hybrid weights must sum to 1.0 so final scores stay normalized in [0, 1]."""
        total = sum(WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_all_weights_are_positive(self):
        assert all(w > 0 for w in WEIGHTS.values())