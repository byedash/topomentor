# GPU overlay: ve cham mau poles/ngon len viewport.
# Toi uu: GPUBatch duoc DUNG SAN trong rebuild() va cache lai; _draw_callback chi
# bind + draw (khong tao VBO moi frame -> muot khi xoay viewport).

import bpy
import gpu
from gpu_extras.batch import batch_for_shader

_handle = None
_shader = None
_batches = {"e": None, "n": None, "ngon": None}   # GPUBatch cache


def _get_shader():
    # UNIFORM_COLOR: builtin hop le o Blender 4.x/5.x.
    global _shader
    if _shader is None:
        _shader = gpu.shader.from_builtin('UNIFORM_COLOR')
    return _shader


def rebuild(obj, ignore_boundary=True):
    # Tinh lai marker va DUNG batch mot lan. Goi khi analyze / bat / refresh.
    global _batches
    from . import topo_utils
    e_co, n_co, ngon_co = topo_utils.gather_markers(obj, ignore_boundary)
    _set_batches(e_co, n_co, ngon_co)


def set_from_coords(e_co, n_co, ngon_co):
    # Nhan thang toa do da tinh san (tranh tinh lai khi analyze_with_markers).
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
    gpu.state.depth_test_set('LESS_EQUAL')          # an cham bi mat che
    size = props.overlay_point_size

    def draw(batch, color, s):
        if batch is None:
            return
        gpu.state.point_size_set(s)
        shader.bind()
        shader.uniform_float("color", tuple(color))
        batch.draw(shader)

    draw(_batches["n"], props.color_n_pole, size)          # N-pole (do)
    draw(_batches["e"], props.color_e_pole, size)          # E-pole (xanh)
    draw(_batches["ngon"], props.color_ngon, size * 0.9)   # tam ngon (vang)

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


def register():
    pass


def unregister():
    disable()
