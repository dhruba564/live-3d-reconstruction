# run_live.py
# LIVE 3D reconstruction from your phone camera with on-the-fly-nvs.
#
# 1. Phone: install "IP Webcam" (Android) or "IP Camera Lite" (iPhone).
#    Connect the phone to the SAME Wi-Fi as this laptop, open the app, press "Start server".
#    The app shows an address like  http://192.168.1.23:8080
# 2. Put that address in PHONE_URL below (keep /video at the end for IP Webcam).
# 3. Press the Run button (or: python run_live.py).
#    After ~1 minute the viewer opens in your browser (http://127.0.0.1:8000/webviewer).
#    Press START there, then film; the 3D scene grows while you move.
# 4. Walk VERY slowly (this GPU handles ~1 frame every 4-5 s), step sideways when turning.
#    Press FINISH in the browser viewer to stop and save. (Ctrl+C keeps only the last backup snapshot.)
#
# Results: D:\track3d_cut_test\demonstration\live_runs\<date_time>\  ->  splat.ply (SuperSplat) + splat_points.ply (MeshLab)

import datetime
import glob
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
import webbrowser

# ---------------- SETTINGS ----------------
PHONE_URL = "http://10.26.76.144:8080/video"   # <- change to the address your phone app shows
DOWNSAMPLING = 1.5     # 1080p stream / 1.5 -> faster. Use 2 if it is too slow.
ROTATE = 0              # rotate the phone picture clockwise: 0, 90, 180 or 270 (fix sideways/upside-down view)
VIEW_SHARPNESS = 1.0    # browser view render size: 1.0 = full sharpness, 1.5 = faster, 2 = original (blurry, fastest)
JPEG_QUALITY = 90       # browser view picture quality (original 50)
SAVE_EVERY = 15       # backup snapshot every N processed frames (in case it crashes / you press Ctrl+C)
# ------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))   # the "demonstration" folder
OTF_REPO = os.path.join(ROOT, "on-the-fly-nvs")
OTF_PYTHON = os.path.join(OTF_REPO, ".venv", "Scripts", "python.exe")
CONVERTER = os.path.join(ROOT, "tools", "splat_to_pointcloud.py")

# Check the phone stream is reachable before starting the (slow) model loading
print("Checking phone stream:", PHONE_URL)
try:
    urllib.request.urlopen(PHONE_URL, timeout=5).close()
    print("Phone stream OK.")
except Exception as e:
    sys.exit(f"Cannot reach the phone stream ({e}).\n"
             "- Is the app's server started?\n- Same Wi-Fi as the laptop (laptop is 192.168.1.x)?\n"
             "- Is PHONE_URL exactly what the app shows, with /video at the end?")

out_dir = os.path.join(ROOT, "live_runs", datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
env = dict(os.environ, TORCH_HOME=os.path.join(ROOT, "torch_cache"), PYTHONUNBUFFERED="1",
           OTF_ROTATE=str(ROTATE), OTF_VIEW_DIV=str(VIEW_SHARPNESS), OTF_JPEG_QUALITY=str(JPEG_QUALITY))
cmd = [OTF_PYTHON, "train.py", "-s", PHONE_URL, "--downsampling", str(DOWNSAMPLING),
       "--viewer_mode", "web", "--ip", "127.0.0.1", "--save_every", str(SAVE_EVERY), "-m", out_dir]
print(">>>", " ".join(cmd))
print("Starting... models load for ~1 minute, then the viewer opens in your browser:")
print("   http://127.0.0.1:8000/webviewer")
print("Press START there to begin, FINISH when done (that saves the result).\n")

def export(src):
    splat = os.path.join(out_dir, "splat.ply")
    shutil.copy(src, splat)
    clean = os.path.join(out_dir, "splat_clean.ply")
    subprocess.run([OTF_PYTHON, os.path.join(ROOT, "tools", "clean_splat.py"), splat, clean])
    subprocess.run([sys.executable, CONVERTER, splat, os.path.join(out_dir, "splat_points.ply")])
    print("\nSAVED!  Splat for SuperSplat (cleaned):", clean)
    print("        Point cloud (MeshLab):        ", os.path.join(out_dir, "splat_points.ply"))
    print("        Same view as the live demo:    python view_otf.py")


proc = subprocess.Popen(cmd, cwd=OTF_REPO, env=env)
threading.Timer(45, lambda: webbrowser.open("http://127.0.0.1:8000/webviewer")).start()
final_meta = os.path.join(out_dir, "metadata.json")   # written when FINISH has saved everything
final_ply = os.path.join(out_dir, "point_clouds", "anchor_0.ply")
exported = False
try:
    while proc.poll() is None:
        if not exported and os.path.exists(final_meta):
            time.sleep(3)                               # let the files finish writing
            export(final_ply)
            exported = True
            print("\nThe browser viewer stays open so you can look around.")
            print("Press Ctrl+C here when you are done to close everything.")
        time.sleep(1)
except KeyboardInterrupt:
    pass
finally:
    if proc.poll() is None:
        proc.kill()

if not exported:
    # FINISH was not pressed: fall back to the newest backup snapshot
    plys = glob.glob(os.path.join(out_dir, "**", "anchor_0.ply"), recursive=True)
    if not plys:
        sys.exit("No saved splat found in " + out_dir + " (stopped before anything was saved).")
    print("\nFINISH was not pressed - using the last backup snapshot.")
    export(max(plys, key=os.path.getmtime))
