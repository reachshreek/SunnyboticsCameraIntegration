from pathlib import Path

from solar_metadata_tagger.mission import MissionStats
from solar_metadata_tagger.models import TagResult


def result(tmp_path: Path, status: str, i: int) -> TagResult:
    return TagResult(str(i), tmp_path / f"{i}.png", tmp_path / f"{i}.json", status)


def test_metadata_goal_calculation(tmp_path) -> None:
    stats = MissionStats("m1")
    for i in range(95):
        stats.record_result(result(tmp_path, "complete", i))
    for i in range(5):
        stats.record_result(result(tmp_path, "quarantined", 100 + i))
    assert stats.metadata_complete_percent == 95.0
    assert stats.as_dict()["meets_95_percent_metadata_goal"] is True
