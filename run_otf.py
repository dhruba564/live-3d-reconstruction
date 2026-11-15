# run_otf.py
# Video -> sequential frames -> on-the-fly-nvs (Gaussian splat) -> fine-tuning -> viewable .ply files
#
# Usage (from D:\track3d_cut_test\demonstration):
#   python run_otf.py "D:\path\to\video.mp4"
#   python run_otf.py "D:\path\to\video.mp4" --fps 5 --epochs 30
#
# Results go to  D:\track3d_cut_test\demonstration\otf_runs\<video name>\
#   splat.ply         -> open in SuperSplat (https://superspl.at/editor)  [best looking]
#   splat_points.ply  -> plain coloured point cloud for MeshLab / CloudCompare

import argparse
import os
import shutil
import subprocess
import sys

import cv2

# ---------------- SETTINGS (used when you press the Run button) ----------------
VIDEO = r"D:\VID_20261114_144851815.mp4"   # change this to your new video
FPS = 5                                     # frames per second taken from the video
EPOCHS = 30                                 # fine-tuning passes (0 = skip, much faster)
# -------------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))   # the "demonstration" folder
OTF_REPO = os.path.join(ROOT, "on-the-fly-nvs")
OTF_PYTHON = os.path.join(OTF_REPO, ".venv", "Scripts", "python.exe")
CONVERTER = os.path.join(ROOT, "tools", "splat_to_pointcloud.py")

parser = argparse.ArgumentParser()
parser.add_argument("video", nargs="?", default=VIDEO)
parser.add_argument("--fps", type=float, default=FPS, help="frames per second taken from the video (5 is good)")
parser.add_argument("--epochs", type=int, default=EPOCHS, help="fine-tuning passes after the live pass (0 = none, fast)")
parser.add_argument("--max_width", type=int, default=1920, help="shrink frames wider than this (1-2 MP works best)")
args = parser.parse_args()

name = os.path.splitext(os.path.basename(args.video))[0]
run_dir = os.path.join(ROOT, "otf_runs", name)
images_dir = os.path.join(run_dir, "data", "images")
model_dir = os.path.join(run_dir, "model")

# ---- STEP 1: extract frames in order ----
print("\n===== STEP 1: Extracting frames =====")
if os.path.isdir(images_dir):
    shutil.rmtree(images_dir)
os.makedirs(images_dir)
cap = cv2.VideoCapture(args.video)
if not cap.isOpened():
    sys.exit("Could not open video: " + args.video)
video_fps = cap.get(cv2.CAP_PROP_FPS) or 30
step = max(1, round(video_fps / args.fps))
i = k = 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    if i % step == 0:
        h, w = frame.shape[:2]
        if w > args.max_width:
            frame = cv2.resize(frame, (args.max_width, round(h * args.max_width / w)), interpolation=cv2.INTER_AREA)
        cv2.imwrite(os.path.join(images_dir, f"frame_{k:05d}.jpg"), frame, [cv2.IMWRITE_JPEG_QUALITY, 95])
        k += 1
    i += 1
cap.release()
print(f"{k} frames -> {images_dir}")
if k < 10:
    sys.exit("Too few frames. Is the video very short?")

# ---- STEP 2: train on-the-fly-nvs ----
print("\n===== STEP 2: Training on-the-fly-nvs =====")
env = dict(os.environ, TORCH_HOME=os.path.join(ROOT, "torch_cache"), PYTHONUNBUFFERED="1")
cmd = [OTF_PYTHON, "train.py", "-s", os.path.join(run_dir, "data"), "-m", model_dir]
if args.epochs > 0:
    cmd += ["--save_at_finetune_epoch", str(args.epochs)]
print(">>>", " ".join(cmd))
if subprocess.run(cmd, cwd=OTF_REPO, env=env).returncode != 0:
    sys.exit("Training failed. Read the error above.")

# ---- STEP 3: copy result + make a point-cloud version ----
print("\n===== STEP 3: Exporting =====")
final = os.path.join(model_dir, str(args.epochs) if args.epochs > 0 else "", "point_clouds", "anchor_0.ply")
splat = os.path.join(run_dir, "splat.ply")
shutil.copy(final, splat)
subprocess.run([sys.executable, CONVERTER, splat, os.path.join(run_dir, "splat_points.ply")])

print("\nDONE!")
print("  Gaussian splat (SuperSplat):      ", splat)
print("  Point cloud (MeshLab/CloudCompare):", os.path.join(run_dir, "splat_points.ply"))
