# Operators: Analyze, Select, Symmetry check, Tris->Quads fix, Export report, Refresh overlay.

import bmesh
import bpy
from bpy.props import EnumProperty, StringProperty
from bpy.types import Operator
from bpy_extras.io_utils import ExportHelper

from . import topo_utils, overlay


def _redraw_view3d(context):
    for area in context.screen.areas:
        if area.type == 'VIEW_3D':
            area.tag_redraw()


class TOPOMENTOR_OT_analyze(Operator):
    bl_idname = "topomentor.analyze"
    bl_label = "Analyze Topology"
    bl_description = "Scan topology cua mesh dang chon va cham Health Score"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        props = context.scene.topomentor

        # Neu overlay bat: tinh 1 lan cho ca so lieu lan marker.
        if props.overlay_enabled:
            data, (e_co, n_co, ngon_co) = topo_utils.analyze_with_markers(
                obj, ignore_boundary=props.ignore_boundary)
            overlay.set_from_coords(e_co, n_co, ngon_co)
            _redraw_view3d(context)
        else:
            data = topo_utils.analyze_mesh(obj, ignore_boundary=props.ignore_boundary)

        for key in ("verts", "edges", "faces", "tris", "quads", "ngons",
                    "pole_e", "pole_n", "non_manifold", "boundary", "score"):
            setattr(props, key, data[key])
        props.rank = topo_utils.rank_label(data["score"])
        props.has_result = True

        self.report({'INFO'},
                    f"Score {data['score']}/100 ({props.rank}) - "
                    f"ngons:{data['ngons']} nonmanifold:{data['non_manifold']}")
        return {'FINISHED'}


class TOPOMENTOR_OT_select(Operator):
    bl_idname = "topomentor.select"
    bl_label = "Select Problem Geometry"
    bl_description = "Vao Edit Mode va chon san geometry loi de sua tay"
    bl_options = {'REGISTER', 'UNDO'}

    select_type: EnumProperty(
        items=(
            ('NGONS', "N-gons", "Chon mat >4 canh"),
            ('TRIS', "Tris", "Chon mat tam giac"),
            ('POLES', "Poles", "Chon vert valence != 4"),
            ('NONMANIFOLD', "Non-manifold", "Chon canh non-manifold"),
        ),
        default='NGONS',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        props = context.scene.topomentor

        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')

        # Deselect o C-level (nhanh hon vong lap Python tren mesh nang).
        bpy.ops.mesh.select_all(action='DESELECT')

        bm = bmesh.from_edit_mesh(obj.data)
        if self.select_type in {'NGONS', 'TRIS'}:
            context.tool_settings.mesh_select_mode = (False, False, True)
            bm.select_mode = {'FACE'}
        elif self.select_type == 'POLES':
            context.tool_settings.mesh_select_mode = (True, False, False)
            bm.select_mode = {'VERT'}
        else:
            context.tool_settings.mesh_select_mode = (False, True, False)
            bm.select_mode = {'EDGE'}

        count = 0
        if self.select_type == 'NGONS':
            for f in bm.faces:
                if len(f.verts) > 4:
                    f.select = True
                    count += 1
        elif self.select_type == 'TRIS':
            for f in bm.faces:
                if len(f.verts) == 3:
                    f.select = True
                    count += 1
        elif self.select_type == 'POLES':
            for v in bm.verts:
                if v.is_wire or (props.ignore_boundary and v.is_boundary):
                    continue
                if len(v.link_edges) != 4:
                    v.select = True
                    count += 1
        else:  # NONMANIFOLD
            for e in bm.edges:
                if not e.is_manifold:
                    e.select = True
                    count += 1

        bm.select_flush_mode()
        bmesh.update_edit_mesh(obj.data)
        self.report({'INFO'}, f"Selected {count} {self.select_type.lower()}")
        return {'FINISHED'}


class TOPOMENTOR_OT_check_symmetry(Operator):
    bl_idname = "topomentor.check_symmetry"
    bl_label = "Check Symmetry"
    bl_description = "Dem vert khong doi xung qua truc da chon (KDTree)"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        props = context.scene.topomentor
        axis = int(props.symmetry_axis)

        unmatched, total = topo_utils.check_symmetry(obj, axis=axis)
        props.sym_unmatched = unmatched
        props.sym_total = total
        props.sym_checked = True

        self.report({'INFO'}, f"Asymmetric verts: {unmatched}/{total}")
        return {'FINISHED'}


class TOPOMENTOR_OT_tris_to_quads(Operator):
    bl_idname = "topomentor.tris_to_quads"
    bl_label = "Tris to Quads (guided)"
    bl_description = "Gop tam giac thanh quad o toan mesh. Kiem tra lai flow sau khi chay!"
    bl_options = {'REGISTER', 'UNDO'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        prev_mode = obj.mode
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.tris_convert_to_quads()
        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=prev_mode)
        self.report({'INFO'}, "Da gop tris->quads. Nho Analyze lai de xem diem.")
        return {'FINISHED'}


class TOPOMENTOR_OT_refresh_overlay(Operator):
    bl_idname = "topomentor.refresh_overlay"
    bl_label = "Refresh Overlay"
    bl_description = "Tinh lai vi tri poles/ngon cho overlay sau khi sua mesh"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def execute(self, context):
        obj = context.active_object
        props = context.scene.topomentor
        overlay.rebuild(obj, props.ignore_boundary)
        _redraw_view3d(context)
        return {'FINISHED'}


class TOPOMENTOR_OT_export_report(Operator, ExportHelper):
    bl_idname = "topomentor.export_report"
    bl_label = "Export Report (.txt)"
    bl_description = "Xuat bao cao topology ra file text"
    bl_options = {'REGISTER'}

    filename_ext = ".txt"
    filter_glob: StringProperty(default="*.txt", options={'HIDDEN'})

    @classmethod
    def poll(cls, context):
        props = context.scene.topomentor
        return props.has_result

    def execute(self, context):
        p = context.scene.topomentor
        obj = context.active_object
        name = obj.name if obj else "-"
        lines = [
            "TopoMentor Report",
            "=================",
            f"Object      : {name}",
            f"Health Score: {p.score}/100  ({p.rank})",
            "",
            f"Verts / Edges / Faces : {p.verts} / {p.edges} / {p.faces}",
            f"Quads : {p.quads}",
            f"Tris  : {p.tris}",
            f"N-gons: {p.ngons}",
            f"Poles E / N : {p.pole_e} / {p.pole_n}",
            f"Non-manifold edges: {p.non_manifold}",
            f"Boundary edges    : {p.boundary}",
        ]
        if p.sym_checked:
            axis = {'0': 'X', '1': 'Y', '2': 'Z'}[p.symmetry_axis]
            lines += ["", f"Symmetry ({axis}): {p.sym_unmatched}/{p.sym_total} asymmetric verts"]

        with open(self.filepath, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        self.report({'INFO'}, f"Saved report: {self.filepath}")
        return {'FINISHED'}


_classes = (
    TOPOMENTOR_OT_analyze,
    TOPOMENTOR_OT_select,
    TOPOMENTOR_OT_check_symmetry,
    TOPOMENTOR_OT_tris_to_quads,
    TOPOMENTOR_OT_refresh_overlay,
    TOPOMENTOR_OT_export_report,
)


def register():
    for c in _classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
