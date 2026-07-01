# Panel UI (N-panel) + subpanels. Chi doc & ve, khong xu ly data.

import bpy
from bpy.types import Panel


class TOPOMENTOR_PT_main(Panel):
    bl_label = "TopoMentor"
    bl_idname = "TOPOMENTOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TopoMentor"

    def draw(self, context):
        layout = self.layout
        props = context.scene.topomentor

        layout.prop(props, "ignore_boundary")
        row = layout.row(align=True)
        row.operator("topomentor.analyze", icon='ZOOM_ALL')
        row.operator("topomentor.report_popup", text="", icon='TEXT')
        layout.operator("topomentor.ready_check", icon='CHECKBOX_HLT')

        if not props.has_result:
            layout.label(text="Chua co du lieu. Bam Analyze.", icon='INFO')
        else:
            box = layout.box()
            r = box.row()
            r.label(text="Health Score: %d/100" % props.score)
            r.label(text=props.rank, icon='SOLO_ON' if props.score >= 75 else 'ERROR')
            col = box.column(align=True)
            col.label(text="Faces %d  |  V %d  E %d" % (props.faces, props.verts, props.edges))
            col.label(text="Quads %d   Tris %d   N-gons %d" % (props.quads, props.tris, props.ngons))
            col.label(text="Poles  E:%d  N:%d" % (props.pole_e, props.pole_n))
            col.label(text="Non-manifold %d   Boundary %d" % (props.non_manifold, props.boundary))

        layout.label(text="Pie menu: Alt + X", icon='EVENT_X')


class TOPOMENTOR_PT_deep(Panel):
    bl_label = "Deep Analysis"
    bl_idname = "TOPOMENTOR_PT_deep"
    bl_parent_id = "TOPOMENTOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TopoMentor"

    def draw(self, context):
        layout = self.layout
        props = context.scene.topomentor
        layout.operator("topomentor.deep_analyze", icon='VIEWZOOM')
        if props.has_extra:
            col = layout.column(align=True)
            col.label(text="Non-planar quads: %d" % props.non_planar)
            col.label(text="Thin triangles: %d" % props.thin_tris)
            col.label(text="N-gons 5/6/7+: %d / %d / %d" % (props.ngon5, props.ngon6, props.ngon_big))
            col.label(text="Area min: %.5f" % props.area_min)
            col.label(text="Area max: %.5f" % props.area_max)
            col.label(text="Area avg: %.5f" % props.area_avg)


class TOPOMENTOR_PT_select(Panel):
    bl_label = "Select & Fix"
    bl_idname = "TOPOMENTOR_PT_select"
    bl_parent_id = "TOPOMENTOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TopoMentor"

    def draw(self, context):
        layout = self.layout
        grid = layout.grid_flow(row_major=True, columns=2, align=True)
        grid.operator("topomentor.select", text="N-gons").select_type = 'NGONS'
        grid.operator("topomentor.select", text="Tris").select_type = 'TRIS'
        grid.operator("topomentor.select", text="Poles").select_type = 'POLES'
        grid.operator("topomentor.select", text="Non-manifold").select_type = 'NONMANIFOLD'
        grid.operator("topomentor.select", text="Non-quads").select_type = 'NONQUADS'

        layout.separator()
        row = layout.row(align=True)
        row.operator("mesh.grid_fill", text="Grid Fill")
        row.operator("mesh.bridge_edge_loops", text="Bridge")
        layout.operator("topomentor.tris_to_quads", icon='MOD_TRIANGULATE')


class TOPOMENTOR_PT_modeling(Panel):
    bl_label = "Modeling Tools"
    bl_idname = "TOPOMENTOR_PT_modeling"
    bl_parent_id = "TOPOMENTOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TopoMentor"

    def draw(self, context):
        layout = self.layout
        layout.operator("topomentor.quick_setup", icon='MODIFIER')
        layout.operator("topomentor.cleanup", icon='BRUSH_DATA')
        layout.operator("topomentor.symmetrize", icon='MOD_MIRROR')


class TOPOMENTOR_PT_retopo(Panel):
    bl_label = "Retopology"
    bl_idname = "TOPOMENTOR_PT_retopo"
    bl_parent_id = "TOPOMENTOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TopoMentor"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        layout.operator("topomentor.retopo_setup", icon='MOD_SHRINKWRAP')
        layout.operator("topomentor.retopo_snap", icon='SNAP_ON')


class TOPOMENTOR_PT_overlay(Panel):
    bl_label = "Overlay & HUD"
    bl_idname = "TOPOMENTOR_PT_overlay"
    bl_parent_id = "TOPOMENTOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TopoMentor"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.topomentor

        layout.prop(props, "hud_enabled", toggle=True, icon='INFO')
        layout.prop(props, "overlay_enabled", toggle=True, icon='HIDE_OFF')
        layout.prop(props, "overlay_nonmanifold", toggle=True, icon='EDGESEL')
        layout.prop(props, "overlay_asym", toggle=True, icon='MOD_MIRROR')

        col = layout.column()
        col.operator("topomentor.refresh_overlay", icon='FILE_REFRESH')
        col.prop(props, "overlay_point_size")
        col.prop(props, "line_width")
        row = col.row(align=True)
        row.prop(props, "color_n_pole", text="N")
        row.prop(props, "color_e_pole", text="E")
        row.prop(props, "color_ngon", text="Ngon")
        row2 = col.row(align=True)
        row2.prop(props, "color_nonmanifold", text="NM")
        row2.prop(props, "color_asym", text="Asym")


class TOPOMENTOR_PT_tools(Panel):
    bl_label = "Symmetry & Report"
    bl_idname = "TOPOMENTOR_PT_tools"
    bl_parent_id = "TOPOMENTOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TopoMentor"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.topomentor

        row = layout.row(align=True)
        row.prop(props, "symmetry_axis", expand=True)
        layout.operator("topomentor.check_symmetry", icon='MOD_MIRROR')
        if props.sym_checked:
            icon = 'CHECKMARK' if props.sym_unmatched == 0 else 'ERROR'
            layout.label(text="Asymmetric: %d/%d" % (props.sym_unmatched, props.sym_total), icon=icon)

        layout.separator()
        layout.operator("topomentor.export_report", icon='FILE_TEXT')


_classes = (
    TOPOMENTOR_PT_main,
    TOPOMENTOR_PT_deep,
    TOPOMENTOR_PT_select,
    TOPOMENTOR_PT_modeling,
    TOPOMENTOR_PT_retopo,
    TOPOMENTOR_PT_overlay,
    TOPOMENTOR_PT_tools,
)


def register():
    for c in _classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
