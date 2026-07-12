"""
download_models.py  -  Downloads the OpenCV ONNX model files needed for face
recognition. Run once before starting the app:
    python download_models.py
"""
import urllib.request
import os
import sys

MODELS = {
    "face_detection_yunet_2023mar.onnx": (
        "yunet.onnx",
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx"
    ),
    "face_recognition_sface_2021dec.onnx": (
        "sface.onnx",
        "https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx"
    ),
}

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def download(url, dest):
    print(f"Downloading {os.path.basename(dest)} ...")
    def reporthook(count, block_size, total_size):
        if total_size > 0:
            pct = min(count * block_size * 100 // total_size, 100)
            sys.stdout.write(f"\r  {pct}%")
            sys.stdout.flush()
    urllib.request.urlretrieve(url, dest, reporthook)
    print(f"\r  Done -> {dest}")

def main():
    for _label, (filename, url) in MODELS.items():
        dest = os.path.join(BASE_DIR, filename)
        if os.path.exists(dest):
            print(f"  {filename} already exists, skipping.")
        else:
            download(url, dest)
    print("\nAll models ready. You can now run:  python app.py")

if __name__ == "__main__":
    main()
