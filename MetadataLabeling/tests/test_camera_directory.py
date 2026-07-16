from solar_metadata_tagger.camera.directory import DirectoryCameraSource
from solar_metadata_tagger.config import CameraConfig


def test_directory_camera_captures_in_order(tmp_path, png_factory) -> None:
    png_factory(tmp_path / "b.png")
    png_factory(tmp_path / "a.png")
    camera = DirectoryCameraSource(CameraConfig(source="directory", source_directory=tmp_path))
    camera.open()
    first = camera.capture(tmp_path / "spool")
    second = camera.capture(tmp_path / "spool")
    assert first.image_path.name == "a.png"
    assert second.image_path.name == "b.png"
    camera.close()
