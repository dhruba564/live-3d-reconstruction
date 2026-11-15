# setup.ps1 - set up the demonstration from scratch on Windows.
#
# Prerequisites: Python 3.12, Git, NVIDIA driver, CUDA Toolkit 12.8,
#                Visual Studio 2022 Build Tools with "Desktop development with C++".
#
# Run from this folder in PowerShell:
#     powershell -ExecutionPolicy Bypass -File setup.ps1
#
# Skips any step that is already done, so it is safe to run again.

$ErrorActionPreference = "Stop"
$Root     = $PSScriptRoot
$Repo     = Join-Path $Root "on-the-fly-nvs"
$Commit   = "4ae0ad1d0b9d67f199dc68161227cf279c79a473"   # version this demo was tested with
$VenvPy   = Join-Path $Repo ".venv\Scripts\python.exe"
$VcVars   = "C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat"
$CudaHome = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.8"
$env:PIP_CACHE_DIR = Join-Path $Root ".pip-cache"

Write-Host "`n=== 1/5  Get on-the-fly-nvs ===" -ForegroundColor Cyan
if (-not (Test-Path (Join-Path $Repo "train.py"))) {
    git clone --recursive https://github.com/graphdeco-inria/on-the-fly-nvs.git $Repo
    git -C $Repo checkout $Commit
    git -C $Repo submodule update --init --recursive
} else { Write-Host "already present" }

Write-Host "`n=== 2/5  Apply demo patches (rotation, sharper web viewer, low-RAM saving) ===" -ForegroundColor Cyan
$Patch = Join-Path $Root "patches\on-the-fly-nvs.patch"
git -C $Repo apply --check $Patch 2>$null
if ($LASTEXITCODE -eq 0) { git -C $Repo apply $Patch; Write-Host "patched" }
else { Write-Host "already applied (or repo modified) - skipping" }

Write-Host "`n=== 3/5  Create the on-the-fly-nvs environment ===" -ForegroundColor Cyan
if (-not (Test-Path $VenvPy)) { python -m venv (Join-Path $Repo ".venv") }
& $VenvPy -m pip install --upgrade pip
& $VenvPy -m pip install torch==2.7.0 torchvision==0.22.0 xformers==0.0.30 --index-url https://download.pytorch.org/whl/cu128
& $VenvPy -m pip install -r (Join-Path $Root "requirements-onthefly.txt")

Write-Host "`n=== 4/5  Compile CUDA extensions (takes several minutes) ===" -ForegroundColor Cyan
if (-not (Test-Path $VcVars)) { throw "Visual Studio Build Tools not found at $VcVars - edit `$VcVars in setup.ps1" }
$Build = "call `"$VcVars`" >nul && set DISTUTILS_USE_SDK=1 && set TORCH_CUDA_ARCH_LIST=8.6 && " +
         "set `"CUDA_HOME=$CudaHome`" && cd /d `"$Repo`" && " +
         "`"$VenvPy`" -m pip install --no-build-isolation -r requirements.txt"
cmd /c $Build
if ($LASTEXITCODE -ne 0) { throw "Building the CUDA extensions failed - see the messages above." }

Write-Host "`n=== 5/5  Launcher packages for your normal Python ===" -ForegroundColor Cyan
python -m pip install -r (Join-Path $Root "requirements.txt")

& $VenvPy -c "import torch, cupy, diff_gaussian_rasterization, simple_knn, fused_ssim; print('CUDA available:', torch.cuda.is_available())"
Write-Host "`nSetup complete. Model weights download automatically on the first run." -ForegroundColor Green
Write-Host "Note: TORCH_CUDA_ARCH_LIST=8.6 targets RTX 30xx GPUs; change it for other GPUs (e.g. 8.9 for RTX 40xx)."
