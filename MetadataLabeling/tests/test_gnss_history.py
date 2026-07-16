from datetime import datetime, timedelta, timezone

from solar_metadata_tagger.gnss import FixHistoryStore
from solar_metadata_tagger.models import GnssFix


def fix(at, lat):
    return GnssFix(latitude=lat, longitude=-121.0, received_at_utc=at, fix_quality=1)


def test_selects_closest_fix_at_or_before_capture() -> None:
    capture = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    store = FixHistoryStore()
    store.update(fix(capture - timedelta(seconds=2), 1.0))
    store.update(fix(capture - timedelta(milliseconds=100), 2.0))
    store.update(fix(capture + timedelta(milliseconds=50), 3.0))
    selected = store.select_for_capture(capture, max_age_s=3, future_tolerance_s=0.25)
    assert selected is not None and selected.latitude == 2.0


def test_future_fix_used_only_within_tolerance() -> None:
    capture = datetime(2026, 7, 16, 12, 0, tzinfo=timezone.utc)
    store = FixHistoryStore()
    store.update(fix(capture + timedelta(milliseconds=100), 1.0))
    assert store.select_for_capture(capture, max_age_s=2, future_tolerance_s=0.25) is not None
    assert store.select_for_capture(capture, max_age_s=2, future_tolerance_s=0.05) is None
