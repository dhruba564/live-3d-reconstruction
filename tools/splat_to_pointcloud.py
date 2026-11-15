"""Convert a Gaussian-splat .ply into a normal coloured point cloud .ply (x y z red green blue)
that CloudCompare / MeshLab can display. Faint, huge and far-away splats are removed.

Usage: python splat_to_pointcloud.py splat.ply out_points.ply
"""
import sys
import numpy as np

SH_C0 = 0.28209479177387814
TYPES = {"float": "<f4", "double": "<f8", "uchar": "u1", "int": "<i4", "uint": "<u4"}


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


v = read_vertices(sys.argv[1])
xyz = np.stack([v["x"], v["y"], v["z"]], 1)
rgb = np.clip(0.5 + SH_C0 * np.stack([v["f_dc_0"], v["f_dc_1"], v["f_dc_2"]], 1), 0, 1)
opacity = 1 / (1 + np.exp(-v["opacity"]))
dist = np.linalg.norm(xyz - np.median(xyz, 0), axis=1)
radius = np.percentile(dist, 98) * 1.5
max_scale = np.exp(np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1)).max(1)
keep = (opacity > 0.1) & (dist < radius) & (max_scale < radius * 0.05)

out = np.empty(keep.sum(), dtype=[("x", "<f4"), ("y", "<f4"), ("z", "<f4"),
                                  ("red", "u1"), ("green", "u1"), ("blue", "u1")])
out["x"], out["y"], out["z"] = xyz[keep].T
out["red"], out["green"], out["blue"] = (rgb[keep] * 255).astype(np.uint8).T
with open(sys.argv[2], "wb") as f:
    f.write(("ply\nformat binary_little_endian 1.0\nelement vertex %d\n"
             "property float x\nproperty float y\nproperty float z\n"
             "property uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n"
             % len(out)).encode())
    out.tofile(f)
print(f"kept {len(out)} of {len(v)} splats -> {sys.argv[2]}")
