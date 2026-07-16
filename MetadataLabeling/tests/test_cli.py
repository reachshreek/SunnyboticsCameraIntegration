import json

from solar_metadata_tagger.cli import main


def test_bad_timestamp_returns_structured_error(tmp_path, png_factory, capsys) -> None:
    image = png_factory(tmp_path / "frame.png")
    config = tmp_path / "config.json"
    config.write_text(json.dumps({
        "robot_id": "robot-1",
        "mission_id": "mission-1",
        "storage": {"root": str(tmp_path / "out"), "min_free_gb": 0, "emergency_free_gb": 0},
        "camera": {"source": "directory", "source_directory": str(tmp_path)},
        "gnss": {"enabled": False},
        "required_fields": ["latitude", "longitude", "row", "panel"]
    }))
    code = main(["tag", "--config", str(config), "--image", str(image), "--captured-at", "bad-time"])
    captured = capsys.readouterr()
    assert code == 2
    payload = json.loads(captured.err)
    assert payload["error_code"] == "TIMESTAMP_INVALID"
    assert "Traceback" not in captured.err
