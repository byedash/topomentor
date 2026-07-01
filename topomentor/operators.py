# Operators: Analyze, Select, Symmetry, Tris->Quads, Export, Refresh, + popup tools.

import bmesh
import bpy
from bpy.props import (
    EnumProperty, StringProperty, BoolProperty, FloatProperty, IntProperty,
)
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
            ('NONQUADS', "Non-quads", "Chon moi mat khong phai quad (tris + ngons)"),
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

        bpy.ops.mesh.select_all(action='DESELECT')

        bm = bmesh.from_edit_mesh(obj.data)
        if self.select_type in {'NGONS', 'TRIS', 'NONQUADS'}:
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
        elif self.select_type == 'NONQUADS':
            for f in bm.faces:
                if len(f.verts) != 4:
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


class TOPOMENTOR_OT_quick_setup(Operator):
    """Popup dung base modeling: Mirror + Shade Smooth + Subdiv + Statistics."""
    bl_idname = "topomentor.quick_setup"
    bl_label = "Modeling Setup"
    bl_description = "Popup: dung nhanh base modeling (mirror, shade smooth, subdiv, stats)"
    bl_options = {'REGISTER', 'UNDO'}

    use_mirror: BoolProperty(name="Mirror Modifier", default=True)
    mirror_x: BoolProperty(name="X", default=True)
    mirror_y: BoolProperty(name="Y", default=False)
    mirror_z: BoolProperty(name="Z", default=False)
    shade_smooth: BoolProperty(name="Shade Smooth", default=True)
    auto_smooth: BoolProperty(name="Smooth by Angle", default=True)
    add_subsurf: BoolProperty(name="Subdivision Modifier", default=False)
    subsurf_levels: IntProperty(name="Levels", default=1, min=1, max=4)
    show_stats: BoolProperty(name="Viewport Statistics", default=True)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=280)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "use_mirror")
        row = layout.row(align=True)
        row.enabled = self.use_mirror
        row.prop(self, "mirror_x")
        row.prop(self, "mirror_y")
        row.prop(self, "mirror_z")
        layout.prop(self, "shade_smooth")
        layout.prop(self, "auto_smooth")
        layout.prop(self, "add_subsurf")
        r = layout.row()
        r.enabled = self.add_subsurf
        r.prop(self, "subsurf_levels")
        layout.prop(self, "show_stats")

    def execute(self, context):
        obj = context.active_object
        done = []
        if self.use_mirror:
            m = obj.modifiers.new("Mirror", 'MIRROR')
            m.use_axis = (self.mirror_x, self.mirror_y, self.mirror_z)
            done.append("mirror")
        if self.shade_smooth:
            bpy.ops.object.shade_smooth()
            done.append("smooth")
        if self.auto_smooth:
            try:
                bpy.ops.object.shade_auto_smooth()
                done.append("auto-smooth")
            except Exception:
                pass
        if self.add_subsurf:
            m = obj.modifiers.new("Subdivision", 'SUBSURF')
            m.levels = self.subsurf_levels
            done.append("subsurf")
        if self.show_stats:
            try:
                context.space_data.overlay.show_stats = True
                done.append("stats")
            except Exception:
                pass
        self.report({'INFO'}, "Setup: " + (", ".join(done) if done else "nothing selected"))
        return {'FINISHED'}


class TOPOMENTOR_OT_cleanup(Operator):
    """Popup ve sinh mesh truoc khi model: merge, loose, normals, fill holes."""
    bl_idname = "topomentor.cleanup"
    bl_label = "Mesh Cleanup"
    bl_description = "Popup: ve sinh mesh (merge by distance, delete loose, recalc normals, fill holes)"
    bl_options = {'REGISTER', 'UNDO'}

    merge_distance: BoolProperty(name="Merge by Distance", default=True)
    merge_threshold: FloatProperty(name="Distance", default=0.0001, min=0.0, precision=5)
    delete_loose: BoolProperty(name="Delete Loose", default=True)
    recalc_normals: BoolProperty(name="Recalculate Normals (Outside)", default=True)
    fill_holes: BoolProperty(name="Fill Holes", default=False)

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=280)

    def draw(self, context):
        layout = self.layout
        layout.prop(self, "merge_distance")
        r = layout.row()
        r.enabled = self.merge_distance
        r.prop(self, "merge_threshold")
        layout.prop(self, "delete_loose")
        layout.prop(self, "recalc_normals")
        layout.prop(self, "fill_holes")

    def execute(self, context):
        obj = context.active_object
        prev_mode = obj.mode
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        done = []
        if self.merge_distance:
            bpy.ops.mesh.remove_doubles(threshold=self.merge_threshold)
            done.append("merge")
        if self.delete_loose:
            bpy.ops.mesh.delete_loose()
            done.append("loose")
        if self.recalc_normals:
            bpy.ops.mesh.normals_make_consistent(inside=False)
            done.append("normals")
        if self.fill_holes:
            bpy.ops.mesh.fill_holes(sides=0)
            done.append("fill")
        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=prev_mode)
        self.report({'INFO'}, "Cleanup: " + (", ".join(done) if done else "nothing selected"))
        return {'FINISHED'}


class TOPOMENTOR_OT_symmetrize(Operator):
    """Popup: ep doi xung nua mesh sang nua kia theo huong chon."""
    bl_idname = "topomentor.symmetrize"
    bl_label = "Symmetrize"
    bl_description = "Popup: ep doi xung mesh theo truc/huong chon"
    bl_options = {'REGISTER', 'UNDO'}

    direction: EnumProperty(
        name="Direction",
        items=(
            ('POSITIVE_X', "+X to -X", ""),
            ('NEGATIVE_X', "-X to +X", ""),
            ('POSITIVE_Y', "+Y to -Y", ""),
            ('NEGATIVE_Y', "-Y to +Y", ""),
            ('POSITIVE_Z', "+Z to -Z", ""),
            ('NEGATIVE_Z', "-Z to +Z", ""),
        ),
        default='POSITIVE_X',
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return obj is not None and obj.type == 'MESH'

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=240)

    def draw(self, context):
        self.layout.prop(self, "direction")

    def execute(self, context):
        obj = context.active_object
        prev_mode = obj.mode
        if obj.mode != 'EDIT':
            bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.mesh.symmetrize(direction=self.direction)
        if prev_mode != 'EDIT':
            bpy.ops.object.mode_set(mode=prev_mode)
        self.report({'INFO'}, "Symmetrized: " + self.direction)
        return {'FINISHED'}


class TOPOMENTOR_OT_report_popup(Operator):
    """Popup noi hien so lieu topology (khong can mo N-panel)."""
    bl_idname = "topomentor.report_popup"
    bl_label = "Topology Report"
    bl_description = "Popup noi hien Health Score va so lieu"
    bl_options = {'REGISTER'}

    @classmethod
    def poll(cls, context):
        return context.scene.topomentor.has_result

    def invoke(self, context, event):
        return context.window_manager.invoke_popup(self, width=260)

    def draw(self, context):
        p = context.scene.topomentor
        layout = self.layout
        layout.label(text="Health Score: %d/100 (%s)" % (p.score, p.rank),
                     icon='SOLO_ON' if p.score >= 75 else 'ERROR')
        col = layout.column(align=True)
        col.label(text="Faces %d  |  V %d  E %d" % (p.faces, p.verts, p.edges))
        col.label(text="Quads %d   Tris %d   N-gons %d" % (p.quads, p.tris, p.ngons))
        col.label(text="Poles  E:%d  N:%d" % (p.pole_e, p.pole_n))
        col.label(text="Non-manifold %d   Boundary %d" % (p.non_manifold, p.boundary))

    def execute(self, context):
        return {'FINISHED'}


_classes = (
    TOPOMENTOR_OT_analyze,
    TOPOMENTOR_OT_select,
    TOPOMENTOR_OT_check_symmetry,
    TOPOMENTOR_OT_tris_to_quads,
    TOPOMENTOR_OT_refresh_overlay,
    TOPOMENTOR_OT_export_report,
    TOPOMENTOR_OT_quick_setup,
    TOPOMENTOR_OT_cleanup,
    TOPOMENTOR_OT_symmetrize,
    TOPOMENTOR_OT_report_popup,
)


def register():
    for c in _classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
