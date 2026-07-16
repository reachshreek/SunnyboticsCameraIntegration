from datetime import datetime, timezone

from solar_metadata_tagger.ids import generate_image_id


def test_image_ids_are_unique_and_sortable_prefix() -> None:
    captured = datetime(2026, 7, 15, 12, 34, 56, 123456, tzinfo=timezone.utc)
    first = generate_image_id("robot-1", "mission-1", captured)
    second = generate_image_id("robot-1", "mission-1", captured)
    assert first != second
    assert first.startswith("robot-1--mission-1--20260715T123456.123456Z--")
