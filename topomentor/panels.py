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
        layout.operator("topomentor.analyze", icon='ZOOM_ALL')

        if not props.has_result:
            layout.label(text="Chua co du lieu. Bam Analyze.", icon='INFO')
            return

        box = layout.box()
        row = box.row()
        row.label(text=f"Health Score: {props.score}/100")
        row.label(text=props.rank, icon='SOLO_ON' if props.score >= 75 else 'ERROR')

        col = box.column(align=True)
        col.label(text=f"Faces {props.faces}  |  V {props.verts}  E {props.edges}")
        col.label(text=f"Quads {props.quads}   Tris {props.tris}   N-gons {props.ngons}")
        col.label(text=f"Poles  E:{props.pole_e}  N:{props.pole_n}")
        col.label(text=f"Non-manifold {props.non_manifold}   Boundary {props.boundary}")


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

        layout.separator()
        layout.operator("topomentor.tris_to_quads", icon='MOD_TRIANGULATE')


class TOPOMENTOR_PT_overlay(Panel):
    bl_label = "Overlay"
    bl_idname = "TOPOMENTOR_PT_overlay"
    bl_parent_id = "TOPOMENTOR_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "TopoMentor"
    bl_options = {'DEFAULT_CLOSED'}

    def draw(self, context):
        layout = self.layout
        props = context.scene.topomentor

        layout.prop(props, "overlay_enabled", toggle=True, icon='HIDE_OFF')
        col = layout.column()
        col.enabled = props.overlay_enabled
        col.operator("topomentor.refresh_overlay", icon='FILE_REFRESH')
        col.prop(props, "overlay_point_size")
        row = col.row(align=True)
        row.prop(props, "color_n_pole", text="N")
        row.prop(props, "color_e_pole", text="E")
        row.prop(props, "color_ngon", text="Ngon")


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
            layout.label(text=f"Asymmetric: {props.sym_unmatched}/{props.sym_total}", icon=icon)

        layout.separator()
        layout.operator("topomentor.export_report", icon='TEXT')


_classes = (
    TOPOMENTOR_PT_main,
    TOPOMENTOR_PT_select,
    TOPOMENTOR_PT_overlay,
    TOPOMENTOR_PT_tools,
)


def register():
    for c in _classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
