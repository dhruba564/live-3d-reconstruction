r"""Open an on-the-fly-nvs result in its own viewer (renders the splat exactly like during the live demo).

Usage:
    python view_otf.py                      -> newest run in live_runs\ or otf_runs\
    python view_otf.py D:\track3d_cut_test\demonstration\live_runs\20261115_104113

Controls: W A S D Q E move, I J K L U O rotate (mouse also works in the window).
"""
import glob
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))   # the "demonstration" folder
OTF_REPO = os.path.join(ROOT, "on-the-fly-nvs")
OTF_PYTHON = os.path.join(OTF_REPO, ".venv", "Scripts", "python.exe")


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


if len(sys.argv) > 1:
    run = sys.argv[1]
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
