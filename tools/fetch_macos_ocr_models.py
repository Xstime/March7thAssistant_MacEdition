"""Fetch the exact RapidOCR models used in the macOS bundle, verifying hashes."""
import hashlib
import os
from pathlib import Path
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1] / "assets" / "ocr" / "models"
BASE = "https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/v3.8.0/onnx/PP-OCRv4"
MODELS = {
    "det/ch_PP-OCRv4_det_mobile.onnx": "d2a7720d45a54257208b1e13e36a8479894cb74155a5efe29462512d42f49da9",
    "cls/ch_ppocr_mobile_v2.0_cls_mobile.onnx": "e47acedf663230f8863ff1ab0e64dd2d82b838fceb5957146dab185a89d6215c",
    "rec/ch_PP-OCRv4_rec_mobile.onnx": "48fc40f24f6d2a207a2b1091d3437eb3cc3eb6b676dc3ef9c37384005483683b",
}


def digest(path):
    hasher = hashlib.sha256()
    with open(path, "rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    for relative, expected in MODELS.items():
        target = ROOT / Path(relative).name
        if target.is_file() and digest(target) == expected:
            print(f"Verified {target.name}")
            continue
        fd, temporary = tempfile.mkstemp(prefix=".model-", dir=ROOT)
        try:
            with os.fdopen(fd, "wb") as output, urllib.request.urlopen(f"{BASE}/{relative}", timeout=60) as response:
                while chunk := response.read(1024 * 1024):
                    output.write(chunk)
            if digest(temporary) != expected:
                raise ValueError(f"SHA-256 mismatch for {relative}")
            os.replace(temporary, target)
            print(f"Downloaded and verified {target.name}")
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)


if __name__ == "__main__":
    main()
