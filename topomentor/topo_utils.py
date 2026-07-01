# Logic thuan: numpy-vectorized cho Object Mode (nhanh), bmesh cho Edit Mode.
# KHONG import bpy.ops, KHONG ve UI.

import bmesh
import numpy as np
from mathutils import kdtree


# =========================================================================== #
#  CORE numpy (Object Mode) - vectorized, khong Python per-element loop
# =========================================================================== #
def _core_numpy(me, ignore_boundary):
    n_poly = len(me.polygons)
    n_edge = len(me.edges)
    n_vert = len(me.vertices)
    n_loop = len(me.loops)

    # --- Dem loai mat: 1 lan foreach_get 'loop_total' ---
    loop_total = np.empty(n_poly, dtype=np.int32)
    me.polygons.foreach_get("loop_total", loop_total)
    tris = int(np.count_nonzero(loop_total == 3))
    quads = int(np.count_nonzero(loop_total == 4))
    ngons = int(np.count_nonzero(loop_total > 4))

    # --- So mat dung moi canh: bincount edge_index tren loops ---
    if n_loop and n_edge:
        loop_edge = np.empty(n_loop, dtype=np.int32)
        me.loops.foreach_get("edge_index", loop_edge)
        edge_use = np.bincount(loop_edge, minlength=n_edge)
    else:
        edge_use = np.zeros(n_edge, dtype=np.int64)
    boundary_mask = edge_use == 1
    nonmanifold_mask = (edge_use == 0) | (edge_use > 2)
    boundary = int(boundary_mask.sum())
    non_manifold = int(nonmanifold_mask.sum())

    # --- Valence moi vert: bincount 2 dau moi canh ---
    if n_edge:
        edge_verts = np.empty(n_edge * 2, dtype=np.int32)
        me.edges.foreach_get("vertices", edge_verts)
        valence = np.bincount(edge_verts, minlength=n_vert)
    else:
        edge_verts = np.empty(0, dtype=np.int32)
        valence = np.zeros(n_vert, dtype=np.int64)

    # --- Vert nao thuoc mat (loai wire/loose khoi thong ke poles) ---
    has_face = np.zeros(n_vert, dtype=bool)
    if n_loop:
        loop_vert = np.empty(n_loop, dtype=np.int32)
        me.loops.foreach_get("vertex_index", loop_vert)
        has_face[loop_vert] = True

    # --- Vert bien: 2 dau cua canh boundary ---
    vert_boundary = np.zeros(n_vert, dtype=bool)
    if n_edge:
        ev = edge_verts.reshape(-1, 2)
        vert_boundary[ev[boundary_mask].ravel()] = True

    candidates = has_face.copy()
    if ignore_boundary:
        candidates &= ~vert_boundary

    pole_e_mask = candidates & (valence == 3)
    pole_n_mask = candidates & (valence >= 5)

    return {
        "counts": {
            "verts": n_vert, "edges": n_edge, "faces": n_poly,
            "tris": tris, "quads": quads, "ngons": ngons,
            "pole_e": int(pole_e_mask.sum()), "pole_n": int(pole_n_mask.sum()),
            "non_manifold": non_manifold, "boundary": boundary,
        },
        "pole_e_mask": pole_e_mask,
        "pole_n_mask": pole_n_mask,
        "ngon_poly_idx": np.nonzero(loop_total > 4)[0],
    }


def _markers_from_core(obj, core):
    # Tu core numpy -> toa do world (list tuple) cho overlay.
    me = obj.data
    n_vert = len(me.vertices)

    co = np.empty(n_vert * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)

    M = np.array(obj.matrix_world, dtype=np.float64)   # 4x4 row-major

    def to_world(mask):
        pts = co[mask]
        if len(pts) == 0:
            return []
        homog = np.ones((len(pts), 4), dtype=np.float64)
        homog[:, :3] = pts
        world = homog @ M.T
        return [tuple(p) for p in world[:, :3]]

    e_co = to_world(core["pole_e_mask"])
    n_co = to_world(core["pole_n_mask"])

    ngon_co = [tuple(obj.matrix_world @ me.polygons[int(i)].center)
               for i in core["ngon_poly_idx"]]
    return e_co, n_co, ngon_co


# =========================================================================== #
#  Duong bmesh (Edit Mode)
# =========================================================================== #
def _analyze_bmesh(obj, ignore_boundary):
    bm = bmesh.from_edit_mesh(obj.data)
    tris = quads = ngons = 0
    for f in bm.faces:
        n = len(f.verts)
        if n == 3:
            tris += 1
        elif n == 4:
            quads += 1
        else:
            ngons += 1
    pole_e = pole_n = 0
    for v in bm.verts:
        if v.is_wire or (ignore_boundary and v.is_boundary):
            continue
        val = len(v.link_edges)
        if val == 3:
            pole_e += 1
        elif val >= 5:
            pole_n += 1
    non_manifold = sum(1 for e in bm.edges if not e.is_manifold)
    boundary = sum(1 for e in bm.edges if e.is_boundary)
    return {
        "verts": len(bm.verts), "edges": len(bm.edges), "faces": len(bm.faces),
        "tris": tris, "quads": quads, "ngons": ngons,
        "pole_e": pole_e, "pole_n": pole_n,
        "non_manifold": non_manifold, "boundary": boundary,
    }


def _markers_bmesh(obj, ignore_boundary):
    bm = bmesh.from_edit_mesh(obj.data)
    mw = obj.matrix_world
    e_co, n_co, ngon_co = [], [], []
    for v in bm.verts:
        if v.is_wire or (ignore_boundary and v.is_boundary):
            continue
        val = len(v.link_edges)
        if val == 3:
            e_co.append(tuple(mw @ v.co))
        elif val >= 5:
            n_co.append(tuple(mw @ v.co))
    for f in bm.faces:
        if len(f.verts) > 4:
            ngon_co.append(tuple(mw @ f.calc_center_median()))
    return e_co, n_co, ngon_co


# =========================================================================== #
#  API cong khai (tu chon duong nhanh theo mode)
# =========================================================================== #
def analyze_mesh(obj, ignore_boundary=True):
    if obj.mode == 'EDIT':
        data = _analyze_bmesh(obj, ignore_boundary)
    else:
        data = _core_numpy(obj.data, ignore_boundary)["counts"]
    data["score"] = _health_score(data)
    return data


def analyze_with_markers(obj, ignore_boundary=True):
    if obj.mode == 'EDIT':
        data = _analyze_bmesh(obj, ignore_boundary)
        data["score"] = _health_score(data)
        return data, _markers_bmesh(obj, ignore_boundary)
    core = _core_numpy(obj.data, ignore_boundary)
    data = core["counts"]
    data["score"] = _health_score(data)
    return data, _markers_from_core(obj, core)


def gather_markers(obj, ignore_boundary=True):
    if obj.mode == 'EDIT':
        return _markers_bmesh(obj, ignore_boundary)
    return _markers_from_core(obj, _core_numpy(obj.data, ignore_boundary))


# =========================================================================== #
#  Health score + symmetry
# =========================================================================== #
def _health_score(r):
    faces = r["faces"]
    if faces == 0:
        return 0
    quad_ratio = r["quads"] / faces
    score = 100.0
    score *= (0.4 + 0.6 * quad_ratio)
    score -= r["ngons"] * 4.0
    score -= r["non_manifold"] * 3.0
    score -= r["tris"] * 0.5
    allowed = max(1, int(r["verts"] * 0.05))
    extra = max(0, (r["pole_e"] + r["pole_n"]) - allowed)
    score -= extra * 0.3
    return max(0, min(100, int(round(score))))


def rank_label(score):
    if score >= 90:
        return "Excellent"
    if score >= 75:
        return "Good"
    if score >= 55:
        return "Needs work"
    return "Messy"


def check_symmetry(obj, axis=0, threshold=0.0001):
    if obj.mode == 'EDIT':
        bm = bmesh.from_edit_mesh(obj.data)
        coords = [v.co.copy() for v in bm.verts]
    else:
        me = obj.data
        n = len(me.vertices)
        buf = np.empty(n * 3, dtype=np.float64)
        me.vertices.foreach_get("co", buf)
        coords = buf.reshape(-1, 3)

    size = len(coords)
    kd = kdtree.KDTree(size)
    for i, c in enumerate(coords):
        kd.insert((float(c[0]), float(c[1]), float(c[2])), i)
    kd.balance()

    unmatched = checked = 0
    for c in coords:
        if abs(c[axis]) <= threshold:
            continue
        checked += 1
        mirror = [float(c[0]), float(c[1]), float(c[2])]
        mirror[axis] = -mirror[axis]
        _, _, dist = kd.find(mirror)
        if dist is None or dist > threshold:
            unmatched += 1
    return unmatched, checked
