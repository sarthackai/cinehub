"""
Unit tests for text cleaning and soup-building logic in ml/preprocessing.py.
These test pure functions with no database dependency — fast and reliable.
"""

import pandas as pd

from app.ml.preprocessing import _clean_text, build_content_soup


class TestCleanText:
    def test_lowercases_text(self):
        assert _clean_text("Hello World") == "hello world"

    def test_strips_punctuation(self):
        assert _clean_text("Sci-Fi, Action!") == "sci fi action"

    def test_normalizes_whitespace(self):
        assert _clean_text("too    many   spaces") == "too many spaces"

    def test_handles_none(self):
        assert _clean_text(None) == ""

    def test_handles_empty_string(self):
        assert _clean_text("") == ""

    def test_preserves_numbers(self):
        assert _clean_text("Toy Story 5") == "toy story 5"


class TestBuildContentSoup:
    def _make_df(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame(rows)

    def test_combines_all_fields(self):
        df = self._make_df(
            [
                {
                    "id": "1",
                    "title": "Interstellar",
                    "overview": "A team travels through a wormhole",
                    "language": "en",
                    "genres": ["Science Fiction", "Drama"],
                    "cast": ["Matthew McConaughey"],
                    "directors": ["Christopher Nolan"],
                }
            ]
        )
        result = build_content_soup(df)
        soup = result.iloc[0]["soup"]
        assert "interstellar" in soup
        assert "science fiction" in soup
        assert "wormhole" in soup
        assert "matthew mcconaughey" in soup
        assert "christopher nolan" in soup

    def test_title_weighted_twice(self):
        """Title should appear twice in the soup (weighting strategy)."""
        df = self._make_df(
            [
                {
                    "id": "1",
                    "title": "Interstellar",
                    "overview": "",
                    "language": "en",
                    "genres": [],
                    "cast": [],
                    "directors": [],
                }
            ]
        )
        result = build_content_soup(df)
        soup = result.iloc[0]["soup"]
        assert soup.count("interstellar") == 2

    def test_handles_missing_overview(self):
        df = self._make_df(
            [
                {
                    "id": "1",
                    "title": "Some Movie",
                    "overview": None,
                    "language": "en",
                    "genres": ["Comedy"],
                    "cast": [],
                    "directors": [],
                }
            ]
        )
        result = build_content_soup(df)
        assert len(result) == 1  # should not crash on None overview

    def test_drops_duplicate_ids(self):
        df = self._make_df(
            [
                {"id": "1", "title": "A", "overview": "x", "language": "en", "genres": [], "cast": [], "directors": []},
                {"id": "1", "title": "A", "overview": "x", "language": "en", "genres": [], "cast": [], "directors": []},
            ]
        )
        result = build_content_soup(df)
        assert len(result) == 1

    def test_drops_rows_with_no_usable_text(self):
        df = self._make_df(
            [
                {"id": "1", "title": "", "overview": "", "language": "", "genres": [], "cast": [], "directors": []},
            ]
        )
        result = build_content_soup(df)
        assert len(result) == 0