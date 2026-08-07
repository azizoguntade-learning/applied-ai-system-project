"""Catalog loading reliability tests.

Covers the two failure modes that matter for "handles errors safely":
a catalog that cannot be read at all, and a catalog with individual bad rows.
"""

import pytest

from src.data_loader import load_songs
from src.errors import CatalogError

HEADER = (
    "id,title,artist,genre,mood,energy,tempo_bpm,valence,danceability,acousticness\n"
)
GOOD_ROW = "1,Sunrise City,Neon Echo,pop,happy,0.82,118,0.84,0.79,0.18\n"
SECOND_GOOD_ROW = "2,Library Rain,Paper Lanterns,lofi,chill,0.35,72,0.60,0.58,0.86\n"


def _write(tmp_path, contents, name="songs.csv"):
    path = tmp_path / name
    path.write_text(contents, encoding="utf-8")
    return path


class TestFatalFailures:
    """Cases where there is nothing usable to recommend from."""

    def test_missing_file_raises_catalog_error(self, tmp_path):
        missing = tmp_path / "does_not_exist.csv"
        with pytest.raises(CatalogError) as exc_info:
            load_songs(missing)
        # The message must name the path, or the user cannot act on it.
        assert str(missing) in str(exc_info.value)

    def test_missing_required_column_raises(self, tmp_path):
        bad_header = HEADER.replace(",acousticness", "")
        path = _write(tmp_path, bad_header + "1,T,A,pop,happy,0.8,118,0.8,0.7\n")
        with pytest.raises(CatalogError) as exc_info:
            load_songs(path)
        assert "acousticness" in str(exc_info.value)

    def test_header_only_file_raises(self, tmp_path):
        with pytest.raises(CatalogError):
            load_songs(_write(tmp_path, HEADER))

    def test_all_rows_malformed_raises(self, tmp_path):
        path = _write(tmp_path, HEADER + "x,T,A,pop,happy,nope,118,0.8,0.7,0.2\n")
        with pytest.raises(CatalogError):
            load_songs(path)


class TestSurvivableFailures:
    """One bad row must not take down the rest of the catalog."""

    def test_bad_numeric_row_is_skipped(self, tmp_path):
        bad = "9,Broken,Artist,pop,happy,NOT_A_NUMBER,118,0.8,0.7,0.2\n"
        songs = load_songs(_write(tmp_path, HEADER + GOOD_ROW + bad + SECOND_GOOD_ROW))
        assert [s.title for s in songs] == ["Sunrise City", "Library Rain"]

    def test_short_row_is_skipped(self, tmp_path):
        songs = load_songs(_write(tmp_path, HEADER + GOOD_ROW + "9,Truncated,Artist\n"))
        assert [s.title for s in songs] == ["Sunrise City"]

    def test_skipped_row_is_logged_with_its_line_number(self, tmp_path, caplog):
        bad = "9,Broken,Artist,pop,happy,NOT_A_NUMBER,118,0.8,0.7,0.2\n"
        with caplog.at_level("WARNING", logger="src.data_loader"):
            load_songs(_write(tmp_path, HEADER + GOOD_ROW + bad))
        # Line 3: header is 1, the good row is 2, so the bad row is 3.
        assert "row 3" in caplog.text


class TestHappyPath:
    def test_real_catalog_loads(self, catalog):
        assert len(catalog) == 17
        assert catalog[0].title == "Sunrise City"

    def test_all_numeric_fields_are_floats(self, catalog):
        song = catalog[0]
        for value in (song.energy, song.tempo_bpm, song.valence,
                      song.danceability, song.acousticness):
            assert isinstance(value, float)
