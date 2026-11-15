r"""Print what is inside a Gaussian-splat .ply and flag anything that makes viewers (SuperSplat) show it wrong.

Usage: python check_ply.py path\to\splat.ply
"""
import sys
import numpy as np

TYPES = {"float": "<f4", "double": "<f8", "uchar": "u1", "int": "<i4", "uint": "<u4"}

path = sys.argv[1]
with open(path, "rb") as f:
    header, props, count, in_vertex = [], [], 0, False
    while True:
        line = f.readline().decode("ascii", "ignore").strip()
        header.append(line)
        parts = line.split()
        if line == "end_header":
            break
        if parts[:2] == ["element", "vertex"]:
            count, in_vertex = int(parts[2]), True
        elif parts[:1] == ["element"]:
            in_vertex = False
        elif in_vertex and parts[:1] == ["property"]:
            props.append((parts[2], TYPES[parts[1]]))
    v = np.fromfile(f, dtype=np.dtype(props), count=count)

names = [n for n, _ in props]
n_rest = sum(n.startswith("f_rest_") for n in names)
print(f"File: {path}")
print(f"Format line: {header[1]}")
print(f"Splats: {count:,}   properties: {len(names)}   f_rest: {n_rest} (SH degree {int(np.sqrt(n_rest / 3 + 1) - 1)})")
print("Properties:", ", ".join(n for n in names if not n.startswith("f_rest_")))

problems = []
for needed in ["x", "y", "z", "f_dc_0", "f_dc_1", "f_dc_2", "opacity", "scale_0", "scale_1", "scale_2",
               "rot_0", "rot_1", "rot_2", "rot_3"]:
    if needed not in names:
        problems.append(f"missing property '{needed}'")

def pct(a):
    return "  ".join(f"{q}%={np.percentile(a, q):.3g}" for q in (0, 1, 50, 99, 100))

xyz = np.stack([v["x"], v["y"], v["z"]], 1)
dist = np.linalg.norm(xyz - np.median(xyz, 0), axis=1)
radius = np.percentile(dist, 98)
print(f"\nDistance from centre : {pct(dist)}")
far = (dist > radius * 1.5 * 10).sum()
if far:
    problems.append(f"{far} splats are extremely far away (>10x scene size) -> viewer zooms out / shows garbage")

op = v["opacity"]
print(f"opacity (raw)        : {pct(op)}")
if op.min() >= 0 and op.max() <= 1:
    problems.append("opacity looks already in 0..1 (standard files store logit values)")
print(f"opacity (0..1)       : {pct(1 / (1 + np.exp(-op)))}")

sc = np.stack([v["scale_0"], v["scale_1"], v["scale_2"]], 1)
print(f"scale (raw, log)     : {pct(sc)}")
if sc.min() >= 0:
    problems.append("scales are all positive: probably stored as real sizes, not log (standard = log)")
size = np.exp(sc).max(1)
print(f"splat size (real)    : {pct(size)}")
huge = (size > radius * 1.5 * 0.1).sum()
if huge:
    problems.append(f"{huge} splats are huge (>10% of scene size) -> big coloured smears over the view")

q = np.stack([v["rot_0"], v["rot_1"], v["rot_2"], v["rot_3"]], 1)
print(f"rotation length      : {pct(np.linalg.norm(q, axis=1))}  (any value is OK, viewers normalise)")
bad = (~np.isfinite(np.stack([v[n] for n in names], 1))).any(1).sum()
if bad:
    problems.append(f"{bad} splats contain NaN/inf values")

print("\nRESULT:", "looks standard, no problems found" if not problems else "")
for p in problems:
    print("  -", p)
if problems:
    print("Fix:  python tools_scripts\\clean_splat.py <in.ply> <out_clean.ply>   then open the _clean file")
