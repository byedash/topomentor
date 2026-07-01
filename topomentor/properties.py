# PropertyGroup: setting + ket qua analyze/deep + checklist + overlay/HUD, gan vao Scene.

import bpy
from bpy.props import (
    BoolProperty, IntProperty, FloatProperty, StringProperty,
    FloatVectorProperty, EnumProperty, PointerProperty,
)
from bpy.types import PropertyGroup

from . import overlay


def _redraw(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


def _overlay_toggled(self, context):
    if self.overlay_enabled:
        obj = context.active_object
        if obj and obj.type == 'MESH':
            overlay.rebuild(obj, self.ignore_boundary)
    overlay.sync_visual()
    _redraw(context)


def _nm_toggled(self, context):
    if self.overlay_nonmanifold:
        obj = context.active_object
        if obj and obj.type == 'MESH':
            overlay.rebuild_nm(obj)
    overlay.sync_visual()
    _redraw(context)


def _asym_toggled(self, context):
    if self.overlay_asym:
        obj = context.active_object
        if obj and obj.type == 'MESH':
            overlay.rebuild_asym(obj, int(self.symmetry_axis))
    overlay.sync_visual()
    _redraw(context)


def _hud_toggled(self, context):
    if self.hud_enabled:
        overlay.enable_hud()
    else:
        overlay.disable_hud()
    _redraw(context)


class TopoMentorProps(PropertyGroup):
    # --- setting phan tich ---
    ignore_boundary: BoolProperty(
        name="Ignore Boundary Poles",
        description="Bo qua vert bien khi dem poles (valence != 4 o bien la binh thuong)",
        default=True,
    )
    symmetry_axis: EnumProperty(
        name="Symmetry Axis",
        items=(('0', "X", ""), ('1', "Y", ""), ('2', "Z", "")),
        default='0',
    )

    # --- overlay cham ---
    overlay_enabled: BoolProperty(
        name="Show Poles Overlay", default=False, update=_overlay_toggled,
        description="Ve cham mau len poles va tam ngon")
    overlay_nonmanifold: BoolProperty(
        name="Show Non-manifold Lines", default=False, update=_nm_toggled,
        description="Ve duong do dam len cac canh non-manifold")
    overlay_asym: BoolProperty(
        name="Show Asymmetric Verts", default=False, update=_asym_toggled,
        description="Highlight cac vert lech doi xung (theo Symmetry Axis)")
    overlay_point_size: FloatProperty(name="Point Size", default=9.0, min=2.0, max=30.0)
    line_width: FloatProperty(name="Line Width", default=3.0, min=1.0, max=10.0)

    color_e_pole: FloatVectorProperty(name="E-pole", subtype='COLOR', size=4,
        default=(0.2, 0.7, 1.0, 1.0), min=0.0, max=1.0)
    color_n_pole: FloatVectorProperty(name="N-pole", subtype='COLOR', size=4,
        default=(1.0, 0.2, 0.2, 1.0), min=0.0, max=1.0)
    color_ngon: FloatVectorProperty(name="N-gon", subtype='COLOR', size=4,
        default=(1.0, 0.8, 0.1, 1.0), min=0.0, max=1.0)
    color_nonmanifold: FloatVectorProperty(name="Non-manifold", subtype='COLOR', size=4,
        default=(1.0, 0.1, 0.1, 1.0), min=0.0, max=1.0)
    color_asym: FloatVectorProperty(name="Asymmetric", subtype='COLOR', size=4,
        default=(1.0, 0.1, 1.0, 1.0), min=0.0, max=1.0)

    # --- HUD chu ---
    hud_enabled: BoolProperty(name="Show HUD", default=False, update=_hud_toggled,
        description="Hien Score + so lieu dang chu o goc viewport")

    # --- ket qua analyze co ban ---
    has_result: BoolProperty(default=False)
    verts: IntProperty(default=0)
    edges: IntProperty(default=0)
    faces: IntProperty(default=0)
    tris: IntProperty(default=0)
    quads: IntProperty(default=0)
    ngons: IntProperty(default=0)
    pole_e: IntProperty(default=0)
    pole_n: IntProperty(default=0)
    non_manifold: IntProperty(default=0)
    boundary: IntProperty(default=0)
    score: IntProperty(default=0)
    rank: StringProperty(default="")

    # --- ket qua deep analysis ---
    has_extra: BoolProperty(default=False)
    non_planar: IntProperty(default=0)
    thin_tris: IntProperty(default=0)
    ngon5: IntProperty(default=0)
    ngon6: IntProperty(default=0)
    ngon_big: IntProperty(default=0)
    area_min: FloatProperty(default=0.0)
    area_max: FloatProperty(default=0.0)
    area_avg: FloatProperty(default=0.0)

    # --- ket qua symmetry ---
    sym_checked: BoolProperty(default=False)
    sym_unmatched: IntProperty(default=0)
    sym_total: IntProperty(default=0)


_classes = (TopoMentorProps,)


def register():
    for c in _classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.topomentor = PointerProperty(type=TopoMentorProps)


def unregister():
    overlay.disable()
    overlay.disable_hud()
    del bpy.types.Scene.topomentor
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
