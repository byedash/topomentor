# Logic thuan: numpy-vectorized cho Object Mode (nhanh), bmesh cho Edit Mode.
# KHONG import bpy.ops, KHONG ve UI.

import math

import bmesh
import numpy as np
from mathutils import kdtree, geometry


def _get_bmesh(obj):
    """Lay BMesh, ho tro ca Object/Edit Mode.

    Tra (bm, is_edit). Neu is_edit=False, caller PHAI goi bm.free().
    """
    me = obj.data
    if obj.mode == 'EDIT':
        return bmesh.from_edit_mesh(me), True
    bm = bmesh.new()
    bm.from_mesh(me)
    return bm, False


# =========================================================================== #
#  CORE numpy (Object Mode)
# =========================================================================== #
def _core_numpy(me, ignore_boundary):
    n_poly = len(me.polygons)
    n_edge = len(me.edges)
    n_vert = len(me.vertices)
    n_loop = len(me.loops)

    loop_total = np.empty(n_poly, dtype=np.int32)
    me.polygons.foreach_get("loop_total", loop_total)
    tris = int(np.count_nonzero(loop_total == 3))
    quads = int(np.count_nonzero(loop_total == 4))
    ngons = int(np.count_nonzero(loop_total > 4))

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

    if n_edge:
        edge_verts = np.empty(n_edge * 2, dtype=np.int32)
        me.edges.foreach_get("vertices", edge_verts)
        valence = np.bincount(edge_verts, minlength=n_vert)
    else:
        edge_verts = np.empty(0, dtype=np.int32)
        valence = np.zeros(n_vert, dtype=np.int64)

    has_face = np.zeros(n_vert, dtype=bool)
    if n_loop:
        loop_vert = np.empty(n_loop, dtype=np.int32)
        me.loops.foreach_get("vertex_index", loop_vert)
        has_face[loop_vert] = True

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
    me = obj.data
    n_vert = len(me.vertices)

    co = np.empty(n_vert * 3, dtype=np.float64)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)

    M = np.array(obj.matrix_world, dtype=np.float64)

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
#  API cong khai
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

    kd = kdtree.KDTree(len(coords))
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


# =========================================================================== #
#  Deep analysis - non-planar quads, thin tris, ngon breakdown, area
# =========================================================================== #
def analyze_extra(obj, non_planar_deg=10.0, thin_ratio=0.1):
    bm, is_edit = _get_bmesh(obj)
    bm.faces.ensure_lookup_table()

    ngon5 = ngon6 = ngon_big = 0
    non_planar = thin_tris = 0
    areas = []
    for f in bm.faces:
        n = len(f.verts)
        area = f.calc_area()
        areas.append(area)
        if n == 5:
            ngon5 += 1
        elif n == 6:
            ngon6 += 1
        elif n > 6:
            ngon_big += 1

        if n == 4:
            v = f.verts
            n1 = geometry.normal(v[0].co, v[1].co, v[2].co)
            n2 = geometry.normal(v[0].co, v[2].co, v[3].co)
            if n1.length > 0.0 and n2.length > 0.0:
                if math.degrees(n1.angle(n2)) > non_planar_deg:
                    non_planar += 1
        elif n == 3:
            longest = max(e.calc_length() for e in f.edges)
            if longest > 0.0 and area > 0.0:
                height = 2.0 * area / longest
                if (height / longest) < thin_ratio:
                    thin_tris += 1

    res = {
        "ngon5": ngon5, "ngon6": ngon6, "ngon_big": ngon_big,
        "non_planar": non_planar, "thin_tris": thin_tris,
        "area_min": min(areas) if areas else 0.0,
        "area_max": max(areas) if areas else 0.0,
        "area_avg": (sum(areas) / len(areas)) if areas else 0.0,
    }
    if not is_edit:
        bm.free()
    return res


# =========================================================================== #
#  Gather cho visual overlay
# =========================================================================== #
def gather_nonmanifold_lines(obj):
    """Non-manifold = canh dung boi >2 mat, hoac canh loose (0 mat)."""
    bm, is_edit = _get_bmesh(obj)
    bm.edges.ensure_lookup_table()
    mw = obj.matrix_world
    coords = []
    for e in bm.edges:
        nf = len(e.link_faces)
        if nf > 2 or nf == 0:
            coords.append(tuple(mw @ e.verts[0].co))
            coords.append(tuple(mw @ e.verts[1].co))
    if not is_edit:
        bm.free()
    return coords


def gather_asymmetry(obj, axis=0, threshold=0.0001):
    bm, is_edit = _get_bmesh(obj)
    bm.verts.ensure_lookup_table()
    mw = obj.matrix_world

    kd = kdtree.KDTree(len(bm.verts))
    for i, v in enumerate(bm.verts):
        kd.insert(v.co, i)
    kd.balance()

    coords = []
    for v in bm.verts:
        if abs(v.co[axis]) <= threshold:
            continue
        m = v.co.copy()
        m[axis] = -m[axis]
        _, _, dist = kd.find(m)
        if dist is None or dist > threshold:
            coords.append(tuple(mw @ v.co))
    if not is_edit:
        bm.free()
    return coords


def check_transform_applied(obj, tol=0.001):
    s = obj.scale
    r = obj.rotation_euler
    scale_ok = all(abs(c - 1.0) <= tol for c in s)
    rot_ok = all(abs(c) <= tol for c in r)
    return scale_ok and rot_ok


def count_loose(obj):
    bm, is_edit = _get_bmesh(obj)
    loose = 0
    for v in bm.verts:
        if len(v.link_faces) == 0:
            loose += 1
    if not is_edit:
        bm.free()
    return loose
