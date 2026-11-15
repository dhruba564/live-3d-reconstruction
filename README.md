# Live 3D Gaussian Splatting from a Phone Camera

Build a photorealistic 3D model of a room **live**, while you walk through it with your phone,
or from a recorded video. This is a thin set of launchers around
[on-the-fly-nvs](https://github.com/graphdeco-inria/on-the-fly-nvs) (Inria GRAPHDECO, SIGGRAPH 2025),
set up to run on a Windows laptop with a 4 GB GPU.

```
 Phone (IP Webcam) ──Wi-Fi──▶ run_live.py ──▶ on-the-fly-nvs ──▶ browser viewer (live)
                                                    │
 Recorded video ─────────────▶ run_otf.py ──────────┤
                                                    ▼
                               splat.ply / splat_clean.ply / splat_points.ply
                                                    │
                               view_otf.py · SuperSplat · MeshLab
```

No camera calibration and no COLMAP are needed. Camera poses are estimated on the fly.

---

## Contents

| File | What it does |
|---|---|
| `run_live.py` | Live reconstruction from a phone camera stream, with a browser viewer |
| `run_otf.py` | Reconstruction from a recorded video, with optional fine-tuning for higher quality |
| `view_otf.py` | Opens a finished result in on-the-fly-nvs's own viewer |
| `tools/clean_splat.py` | Removes broken splats (far away / huge / invisible) so other viewers show the result correctly |
| `tools/splat_to_pointcloud.py` | Converts a splat to a plain coloured point cloud (for MeshLab / CloudCompare) |
| `tools/check_ply.py` | Prints what is inside a splat `.ply` and flags problems |
| `patches/on-the-fly-nvs.patch` | Small changes to on-the-fly-nvs (see [Changes to on-the-fly-nvs](#changes-to-on-the-fly-nvs)) |
| `setup.ps1` | Sets up everything from scratch |
| `requirements.txt` | Packages for the launcher scripts |
| `requirements-onthefly.txt` | Packages for the on-the-fly-nvs environment |

```
demonstration/
├── run_live.py
├── run_otf.py
├── view_otf.py
├── setup.ps1
├── requirements.txt
├── requirements-onthefly.txt
├── patches/on-the-fly-nvs.patch
├── tools/
├── on-the-fly-nvs/      # created by setup.ps1 (code + .venv + models/)
├── torch_cache/         # created on first run (feature-matcher weights)
├── live_runs/           # outputs of run_live.py
└── otf_runs/            # outputs of run_otf.py
```

---

## Requirements

Tested on:

| | |
|---|---|
| OS | Windows 11 |
| GPU | NVIDIA RTX 3050 Laptop, 4 GB (any CUDA GPU with ≥ 4 GB should work) |
| Python | 3.12 |
| CUDA Toolkit | 12.8 |
| Compiler | Visual Studio 2022 Build Tools ("Desktop development with C++") |
| Phone | Android with **IP Webcam**, or iPhone with **IP Camera Lite** (live mode only) |

About 10 GB of disk space is needed (PyTorch environment plus about 2 GB of model weights downloaded on the first run).

## Installation

```powershell
cd demonstration
powershell -ExecutionPolicy Bypass -File setup.ps1
```

`setup.ps1` clones on-the-fly-nvs at the tested commit, applies `patches/on-the-fly-nvs.patch`,
creates `on-the-fly-nvs/.venv` with PyTorch 2.7 + CUDA 12.8, compiles the CUDA extensions,
and installs the launcher requirements. It skips steps that are already done.

> **Other GPUs:** the script compiles for RTX 30xx (`TORCH_CUDA_ARCH_LIST=8.6`).
> Change it in `setup.ps1` for other cards, e.g. `8.9` for RTX 40xx or `7.5` for RTX 20xx.

<details>
<summary>Manual installation</summary>

```powershell
git clone --recursive https://github.com/graphdeco-inria/on-the-fly-nvs.git
git -C on-the-fly-nvs checkout 4ae0ad1d0b9d67f199dc68161227cf279c79a473
git -C on-the-fly-nvs apply ..\patches\on-the-fly-nvs.patch

python -m venv on-the-fly-nvs\.venv
on-the-fly-nvs\.venv\Scripts\python -m pip install torch==2.7.0 torchvision==0.22.0 xformers==0.0.30 --index-url https://download.pytorch.org/whl/cu128
on-the-fly-nvs\.venv\Scripts\python -m pip install -r requirements-onthefly.txt

# in an "x64 Native Tools Command Prompt for VS 2022":
set DISTUTILS_USE_SDK=1
set TORCH_CUDA_ARCH_LIST=8.6
cd on-the-fly-nvs
.venv\Scripts\python -m pip install --no-build-isolation -r requirements.txt
cd ..

python -m pip install -r requirements.txt
```
</details>

---

## Usage

All scripts have a **SETTINGS** block at the top, so you can edit it and press **▶ Run** in VS Code.
They also work from the terminal.

### 1. Live reconstruction: `run_live.py`

1. **Phone:** install IP Webcam (Android) or IP Camera Lite (iPhone), connect to the **same Wi-Fi** as
   the laptop (or connect the laptop to the phone's hotspot), and tap **Start server**.
2. Put the address the app shows into `PHONE_URL` (keep `/video` at the end for IP Webcam).
3. Run:
   ```powershell
   python run_live.py
   ```
4. After about a minute the viewer opens at **http://127.0.0.1:8000/webviewer**.
   Press **Start**, then walk **slowly sideways** through the scene.
5. Press **Finish** to save. The terminal prints `SAVED!`. Then press `Ctrl+C` to close.

| Setting | Default | Meaning |
|---|---|---|
| `PHONE_URL` | `http://<phone-ip>:8080/video` | Stream address shown by the phone app |
| `DOWNSAMPLING` | `1.5` | Shrinks 1080p frames. `2` is faster and tracks more easily, but shows less detail |
| `ROTATE` | `0` | Rotates the phone picture clockwise (`90`, `180`, `270`) if it arrives sideways |
| `VIEW_SHARPNESS` | `1.0` | Browser render size. `1.0` is full resolution, `2` is the original (blurry, fastest) |
| `JPEG_QUALITY` | `90` | Browser picture quality (the original value is 50) |
| `SAVE_EVERY` | `15` | Backup snapshot every N processed frames |

Viewer buttons: **Start**, **Pause**, **Finish**, and **Free view** (move the 3D camera with the mouse
instead of following the phone).

### 2. From a recorded video: `run_otf.py`

```powershell
python run_otf.py "D:\path\to\video.mp4"
python run_otf.py "D:\path\to\video.mp4" --fps 4 --epochs 20
```

| Option | Default | Meaning |
|---|---|---|
| `video` | `VIDEO` setting | Input video |
| `--fps` | `5` | Frames per second taken from the video |
| `--epochs` | `30` | Fine-tuning passes after the live pass (`0` = skip, much faster, lower quality) |
| `--max_width` | `1920` | Shrinks wider frames (the matcher works best at 1–2 MP) |

A 37-second video takes about 14 minutes for the live pass plus about 20 minutes of fine-tuning on an RTX 3050.

### 3. View a result: `view_otf.py`

```powershell
python view_otf.py                                  # newest run
python view_otf.py live_runs\20261115_104113        # a specific run
```
Opens on-the-fly-nvs's viewer, which renders the scene the same way as during the live demo.
Controls: `W A S D Q E` move, `I J K L U O` rotate.

---

## Outputs

Every run folder (`live_runs/<date_time>/` or `otf_runs/<video name>/`) contains:

| File | Open with |
|---|---|
| `splat_clean.ply` | **[SuperSplat](https://superspl.at/editor)**: drag and drop. Best-looking result (live runs) |
| `splat.ply` | Raw Gaussian splat (standard 3DGS format) |
| `splat_points.ply` | MeshLab / CloudCompare: splat centres as a coloured point cloud |
| `colmap/` | Estimated camera poses (COLMAP binary format) |
| `metadata.json`, `point_clouds/` | Used by `view_otf.py` |

> `splat_points.ply` keeps only the centre of each splat, so it looks much sparser than the real result.
> To see the scene as it really looks, use a splat viewer (SuperSplat or `view_otf.py`).
> If the scene appears upside down in SuperSplat, rotate it 180°.

Check a splat file:
```powershell
python tools\check_ply.py live_runs\20261115_104113\splat.ply
```

---

## Tips for good results

- **Walk sideways, slowly.** Each frame must overlap at least two-thirds with the previous one.
  Don't rotate the camera in place; take a sideways step when turning.
- **Point at textured, static things** like furniture, posters and objects. Avoid plain walls, screens and moving people.
- **Keep the same camera.** Don't switch to the front camera during a run.
- **Nothing appears at first:** the scene starts after about 8 keyframes, and frames only count as keyframes
  once the camera has moved enough. Move the phone.
- **Tracking froze:** slowly point back at the area you filmed last. Tracking can't recover from big jumps.
- **Live mode on a 4 GB GPU** processes about one frame every 4–5 seconds, so cover one area well instead of a whole hall.
- **Laptop:** keep it plugged into power and close heavy apps. Phone hotspot is more reliable than public Wi-Fi.

## Troubleshooting

| Problem | Fix |
|---|---|
| `Cannot reach the phone stream` | App server not started, phone and laptop on different networks, or wrong `PHONE_URL` |
| Browser says *waiting for training loop to begin* | Models are still loading (about 1 min), or no run is active. Check the terminal and refresh the page |
| Browser view is black after **Start** | Not enough camera movement yet (see the tips above) |
| Picture sideways | Set `ROTATE = 90` (or `270`), or hold the phone horizontally |
| Terminal looks stuck after **Finish** | Expected: the viewer stays open. Press `Ctrl+C` |
| Huge smears or empty view in SuperSplat | Open `splat_clean.ply`, or run `tools\clean_splat.py` |
| `CUDA out of memory` | Increase `DOWNSAMPLING`, set `VIEW_SHARPNESS = 1.5`, close other GPU apps |
| CuPy error *libcu++ requires at least C++ 17* | CuPy 14 is installed. Run `pip install "cupy-cuda12x<14"` in the on-the-fly-nvs environment |

## Changes to on-the-fly-nvs

`patches/on-the-fly-nvs.patch` makes three small changes to the upstream code:

| File | Change |
|---|---|
| `dataloaders/stream_dataset.py` | Optional rotation of the phone stream (`OTF_ROTATE`) |
| `webviewer/webviewer.py` | Configurable render resolution and JPEG quality (`OTF_VIEW_DIV`, `OTF_JPEG_QUALITY`) for a sharper browser view |
| `scene/anchor.py` | Memory-efficient `.ply` saving (the original ran out of RAM on Windows) |

Defaults are unchanged when the environment variables are not set.

---

## Credits and license

The reconstruction method is **on-the-fly-nvs** by Inria GRAPHDECO. Its code is under the
[Inria research license](https://github.com/graphdeco-inria/on-the-fly-nvs/blob/main/LICENSE.md),
which allows **non-commercial research and evaluation use only**. That license applies to
everything inside `on-the-fly-nvs/` and to the patch.

```bibtex
@article{meuleman2025onthefly,
  title={On-the-fly Reconstruction for Large-Scale Novel View Synthesis from Unposed Images},
  author={Meuleman, Andreas and Shah, Ishaan and Lanvin, Alexandre and Kerbl, Bernhard and Drettakis, George},
  journal={ACM Transactions on Graphics},
  volume={44},
  number={4},
  year={2025}
}
```
