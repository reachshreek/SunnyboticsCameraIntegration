"""Minimal one-frame example using whichever camera source is in configuration."""

from solar_metadata_tagger import MetadataTaggingService, TaggerConfig
from solar_metadata_tagger.camera import create_camera_source
from solar_metadata_tagger.gnss import FixHistoryStore, SerialGnssReader
from solar_metadata_tagger.logging_utils import configure_logging


def main() -> None:
    config = TaggerConfig.from_file("config/example_config.json")
    configure_logging(config.storage.root / "logs", config.log_level)
    fix_store = FixHistoryStore(config.gnss.history_size)
    gnss = (
        SerialGnssReader(
            fix_store,
            port=config.gnss.port,
            baudrate=config.gnss.baudrate,
            timeout_s=config.gnss.timeout_s,
            reconnect_delay_s=config.gnss.reconnect_delay_s,
        )
        if config.gnss.enabled
        else None
    )
    camera = create_camera_source(config.camera)
    tagger = MetadataTaggingService(config, fix_store=fix_store)

    try:
        if gnss:
            gnss.start()
        camera.open()
        frame = camera.capture(config.storage.effective_spool_dir)
        result = tagger.tag_image(
            frame.image_path,
            captured_at_utc=frame.captured_at_utc,
            captured_monotonic_ns=frame.monotonic_ns,
            camera_metadata=frame.camera_metadata,
            trigger_metadata={"source": "example"},
        )
        print(result.as_dict())
    finally:
        camera.close()
        if gnss:
            gnss.stop()


if __name__ == "__main__":
    main()
