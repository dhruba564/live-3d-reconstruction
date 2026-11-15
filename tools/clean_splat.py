"""Remove outlier Gaussians (far away / huge / invisible) from a 3DGS .ply so viewers don't choke.
Usage: python clean_splat.py in.ply out.ply"""
import sys
import numpy as np
from plyfile import PlyData, PlyElement

src, dst = sys.argv[1], sys.argv[2]
v = PlyData.read(src)["vertex"].data
xyz = np.stack([v["x"], v["y"], v["z"]], 1)
center = np.median(xyz, 0)
dist = np.linalg.norm(xyz - center, axis=1)
radius = np.percentile(dist, 98) * 1.5          # scene radius, robust to the far outliers
max_scale = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1)).max(1)
opacity = 1 / (1 + np.exp(-v["opacity"]))

keep = (dist < radius) & (max_scale < radius * 0.1) & (opacity > 0.02)
print(f"scene radius {radius:.2f}; keeping {keep.sum()} / {len(v)} gaussians")

names = [n for n in v.dtype.names if n not in ("nx", "ny", "nz")]
out = np.empty(keep.sum(), dtype=[(n, "f4") for n in names])
for n in names:
    out[n] = v[n][keep]
PlyData([PlyElement.describe(out, "vertex")]).write(dst)
print("wrote", dst)
