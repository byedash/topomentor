# GPU overlay (cham poles/ngon) + HUD chu (blf).
# Toi uu: GPUBatch dung san trong rebuild() va cache; draw callback chi bind + draw.

import bpy
import blf
import gpu
from gpu_extras.batch import batch_for_shader

_handle = None          # handler cham (POST_VIEW, world space)
_hud_handle = None      # handler HUD chu (POST_PIXEL, pixel space)
_shader = None
_batches = {"e": None, "n": None, "ngon": None}


def _get_shader():
    # UNIFORM_COLOR: builtin hop le o Blender 4.x/5.x.
    global _shader
    if _shader is None:
        _shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    return _shader


# --------------------------------------------------------------------------- #
#  Overlay cham (POST_VIEW)
# --------------------------------------------------------------------------- #
def rebuild(obj, ignore_boundary=True):
    from . import topo_utils
    e_co, n_co, ngon_co = topo_utils.gather_markers(obj, ignore_boundary)
    _set_batches(e_co, n_co, ngon_co)


def set_from_coords(e_co, n_co, ngon_co):
    _set_batches(e_co, n_co, ngon_co)


def _set_batches(e_co, n_co, ngon_co):
    global _batches
    shader = _get_shader()
    _batches = {
        "e": batch_for_shader(shader, 'POINTS', {"pos": e_co}) if e_co else None,
        "n": batch_for_shader(shader, 'POINTS', {"pos": n_co}) if n_co else None,
        "ngon": batch_for_shader(shader, 'POINTS', {"pos": ngon_co}) if ngon_co else None,
    }


def _draw_callback():
    props = getattr(bpy.context.scene, "topomentor", None)
    if props is None or not props.overlay_enabled:
        return
    shader = _get_shader()
    gpu.state.blend_set('ALPHA')
    gpu.state.depth_test_set('LESS_EQUAL')
    size = props.overlay_point_size

    def draw(batch, color, s):
        if batch is None:
            return
        gpu.state.point_size_set(s)
        shader.bind()
        shader.uniform_float("color", tuple(color))
        batch.draw(shader)

    draw(_batches["n"], props.color_n_pole, size)
    draw(_batches["e"], props.color_e_pole, size)
    draw(_batches["ngon"], props.color_ngon, size * 0.9)

    gpu.state.depth_test_set('NONE')
    gpu.state.blend_set('NONE')


def enable():
    global _handle
    if _handle is None:
        _handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_callback, (), 'WINDOW', 'POST_VIEW')


def disable():
    global _handle, _batches
    if _handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_handle, 'WINDOW')
        _handle = None
    _batches = {"e": None, "n": None, "ngon": None}


# --------------------------------------------------------------------------- #
#  HUD chu (POST_PIXEL) - hien Score + counts o goc tren-trai
# --------------------------------------------------------------------------- #
def _draw_hud():
    props = getattr(bpy.context.scene, "topomentor", None)
    if props is None or not props.hud_enabled or not props.has_result:
        return
    region = bpy.context.region
    if region is None:
        return

    font_id = 0
    x = 20
    y = region.height - 40
    lines = [
        "TopoMentor  Score %d/100 (%s)" % (props.score, props.rank),
        "Quads %d   Tris %d   N-gons %d" % (props.quads, props.tris, props.ngons),
        "Poles E%d N%d   Non-manifold %d" % (props.pole_e, props.pole_n, props.non_manifold),
    ]
    blf.size(font_id, 15)   # Blender 4.x/5.x: blf.size(fontid, size)
    for i, ln in enumerate(lines):
        if i == 0:
            if props.score >= 75:
                blf.color(font_id, 0.5, 1.0, 0.5, 1.0)
            else:
                blf.color(font_id, 1.0, 0.6, 0.3, 1.0)
        else:
            blf.color(font_id, 0.9, 0.9, 0.9, 1.0)
        blf.position(font_id, x, y - i * 22, 0)
        blf.draw(font_id, ln)


def enable_hud():
    global _hud_handle
    if _hud_handle is None:
        _hud_handle = bpy.types.SpaceView3D.draw_handler_add(
            _draw_hud, (), 'WINDOW', 'POST_PIXEL')


def disable_hud():
    global _hud_handle
    if _hud_handle is not None:
        bpy.types.SpaceView3D.draw_handler_remove(_hud_handle, 'WINDOW')
        _hud_handle = None


def register():
    pass


def unregister():
    disable()
    disable_hud()
