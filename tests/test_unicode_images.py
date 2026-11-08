"""Windows paths must not silently drop evidence images."""
import cv2
import numpy as np
import pytest

from rea_video import motion
from rea_video.util import read_image, write_image


def test_unicode_image_roundtrip(tmp_path):
    folder = tmp_path / "中文 報告"
    folder.mkdir()
    image = np.zeros((24, 32, 3), np.uint8)
    image[:, :16] = (20, 80, 160)
    image[:, 16:] = (200, 40, 10)
    path = folder / "證據 圖.png"
    write_image(path, image)
    assert path.is_file()
    assert np.array_equal(read_image(path), image)  # preserves BGR order
    jpg = folder / "分鏡.jpg"
    write_image(jpg, image, [cv2.IMWRITE_JPEG_QUALITY, 94])
    assert read_image(jpg).shape == image.shape


def test_missing_or_invalid_image_is_unavailable(tmp_path):
    assert read_image(tmp_path / "不存在.jpg") is None
    path = tmp_path / "損壞.jpg"
    path.write_bytes(b"")
    assert read_image(path) is None
    path.write_bytes(b"not an image")
    assert read_image(path) is None


def test_write_error_is_not_reported_as_success(tmp_path):
    with pytest.raises(OSError):
        write_image(tmp_path / "缺少目錄" / "圖.jpg", np.zeros((8, 8, 3), np.uint8))


def test_element_crops_exist_in_unicode_report(tmp_path, monkeypatch):
    image = np.full((60, 80, 3), (20, 80, 160), np.uint8)
    monkeypatch.setattr(motion, "iter_frames", lambda *a, **kw: iter([image] * 10))
    out = tmp_path / "中文 報告" / "shots"
    data = {"events": [{"kind": "appear", "t0": 0.0, "t1": 0.2, "box": [0.1, 0.1, 0.5, 0.5]}]}
    sheet = motion.element_crops("unused.mp4", None, 0.0, 1.0, data, out, "shot_001", 80)
    crop = data["events"][0]["crop"]
    for relative in (sheet, crop):
        path = out.parent / relative
        assert path.is_file(), f"reported evidence image is missing: {relative}"
        assert read_image(path) is not None
