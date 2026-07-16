import json

from solar_metadata_tagger.config import CaptureConfig
from solar_metadata_tagger.triggers import TriggerProvider


def test_file_trigger_claim_and_complete(tmp_path) -> None:
    root = tmp_path / "triggers"
    incoming = root / "incoming"
    incoming.mkdir(parents=True)
    (incoming / "point.json").write_text(json.dumps({"row": "A", "panel": "001"}))
    provider = TriggerProvider(CaptureConfig(trigger_mode="file", trigger_directory=root, max_images=1))
    trigger = next(iter(provider))
    assert trigger.row == "A"
    assert trigger.source_file is not None and trigger.source_file.parent.name == "processing"
    provider.mark_success(trigger, {"status": "complete"})
    completed = json.loads((root / "processed" / "point.json").read_text())
    assert completed["result"]["status"] == "complete"
