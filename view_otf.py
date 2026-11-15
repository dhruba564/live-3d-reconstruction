r"""Open an on-the-fly-nvs result, or any Gaussian-splat .ply, in on-the-fly-nvs's own viewer.

Usage:
    python view_otf.py                                   -> newest run in live_runs\ or otf_runs\
    python view_otf.py live_runs\20261115_104113         -> a run folder
    python view_otf.py D:\somewhere\splat.ply            -> any standard 3DGS .ply (Brush, SuperSplat, 3DGS ...)

Or set PLY below and press the Run button.

Controls: W A S D Q E move, I J K L U O rotate (mouse also works in the window).
"""
import glob
import json
import os
import shutil
import subprocess
import sys

import numpy as np

# ---------------- SETTINGS (used when you press the Run button) ----------------
PLY = ""   # e.g. r"D:\track3d_cut_test\export.ply"  - leave empty to open the newest run
# -------------------------------------------------------------------------------

ROOT = os.path.dirname(os.path.abspath(__file__))   # the "demonstration" folder
OTF_REPO = os.path.join(ROOT, "on-the-fly-nvs")
OTF_PYTHON = os.path.join(OTF_REPO, ".venv", "Scripts", "python.exe")
VIEW_CACHE = os.path.join(ROOT, ".view_cache")
TYPES = {"float": "<f4", "double": "<f8", "uchar": "u1", "int": "<i4", "uint": "<u4"}


def model_dir_of(run):
    """The folder that holds metadata.json + point_clouds (final save, or newest backup snapshot)."""
    for cand in [run, os.path.join(run, "model")]:
        if os.path.exists(os.path.join(cand, "metadata.json")):
            # fine-tuned runs: prefer the highest fine-tuning epoch folder
            epochs = [d for d in glob.glob(os.path.join(cand, "[0-9]*"))
                      if os.path.exists(os.path.join(d, "metadata.json")) and os.path.basename(d).isdigit()]
            return max(epochs, key=lambda d: int(os.path.basename(d))) if epochs else cand
    snaps = glob.glob(os.path.join(run, "progress", "*", "metadata.json"))
    if snaps:
        return os.path.dirname(max(snaps, key=os.path.getmtime))
    return None


def read_vertices(path):
    with open(path, "rb") as f:
        props, count, in_vertex = [], 0, False
        while True:
            parts = f.readline().decode("ascii", "ignore").split()
            if parts == ["end_header"]:
                break
            if parts[:2] == ["element", "vertex"]:
                count, in_vertex = int(parts[2]), True
            elif parts[:1] == ["element"]:
                in_vertex = False
            elif in_vertex and parts[:1] == ["property"]:
                props.append((parts[2], TYPES[parts[1]]))
        return np.fromfile(f, dtype=np.dtype(props), count=count)


def model_dir_for_ply(ply):
    """Wrap a plain splat .ply in the folder layout the viewer expects (metadata.json + point_clouds/)."""
    v = read_vertices(ply)
    names = v.dtype.names
    for needed in ("x", "y", "z", "f_dc_0", "opacity", "scale_0", "rot_0"):
        if needed not in names:
            sys.exit(f"{ply} is not a Gaussian-splat .ply (missing '{needed}'). "
                     "Plain point clouds can't be shown in this viewer; use MeshLab instead.")
    n_rest = sum(n.startswith("f_rest_") for n in names)
    sh_degree = int(round(np.sqrt(n_rest / 3 + 1))) - 1

    xyz = np.stack([v["x"], v["y"], v["z"]], 1)
    centre = np.median(xyz, 0)
    radius = np.percentile(np.linalg.norm(xyz - centre, axis=1), 90)
    cam = centre - np.array([0, 0, 2.0 * radius])           # start a bit behind the scene, looking +z at it
    Rt = np.eye(4)
    Rt[:3, 3] = -cam                                         # world -> camera

    out = os.path.join(VIEW_CACHE, os.path.splitext(os.path.basename(ply))[0])
    os.makedirs(os.path.join(out, "point_clouds"), exist_ok=True)
    shutil.copyfile(ply, os.path.join(out, "point_clouds", "anchor_0.ply"))
    width, height = 1280, 720
    meta = {
        "config": {"width": width, "height": height, "sh_degree": sh_degree, "f": 0.8 * width},
        "anchors": [{"position": centre.tolist()}],
        "keyframes": [{"info": {"is_test": False}, "Rt": Rt.tolist(), "f": 0.8 * width}],
    }
    with open(os.path.join(out, "metadata.json"), "w") as f:
        json.dump(meta, f)
    return out


target = sys.argv[1] if len(sys.argv) > 1 else PLY
if target and target.lower().endswith(".ply"):
    if not os.path.exists(target):
        sys.exit("File not found: " + target)
    model = model_dir_for_ply(target)
else:
    if target:
        run = target
    else:
        runs = glob.glob(os.path.join(ROOT, "live_runs", "*")) + glob.glob(os.path.join(ROOT, "otf_runs", "*"))
        runs = [r for r in runs if model_dir_of(r)]
        if not runs:
            sys.exit("No on-the-fly results found.")
        run = max(runs, key=os.path.getmtime)
    model = model_dir_of(run)
    if model is None:
        sys.exit("No saved model (metadata.json) found in " + run)

print("Opening:", model)
print(__doc__.split("Controls:")[1].strip())
subprocess.run([OTF_PYTHON, "gaussianviewer.py", "local", model], cwd=OTF_REPO)
