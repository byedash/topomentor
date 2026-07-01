# Pie menu: truy cap nhanh cac lenh TopoMentor bang hotkey (mac dinh Alt+X).

import bpy
from bpy.types import Menu


class TOPOMENTOR_MT_pie(Menu):
    bl_label = "TopoMentor"
    bl_idname = "TOPOMENTOR_MT_pie"

    def draw(self, context):
        pie = self.layout.menu_pie()
        # 8 huong pie: West, East, South, North, NW, NE, SW, SE
        pie.operator("topomentor.analyze", text="Analyze", icon='ZOOM_ALL')
        pie.operator("topomentor.cleanup", text="Cleanup", icon='BRUSH_DATA')
        pie.operator("topomentor.quick_setup", text="Setup", icon='MODIFIER')
        pie.operator("topomentor.symmetrize", text="Symmetrize", icon='MOD_MIRROR')
        op = pie.operator("topomentor.select", text="Sel N-gons", icon='MESH_DATA')
        op.select_type = 'NGONS'
        op2 = pie.operator("topomentor.select", text="Sel Poles", icon='VERTEXSEL')
        op2.select_type = 'POLES'
        pie.operator("topomentor.report_popup", text="Report", icon='TEXT')
        pie.operator("topomentor.refresh_overlay", text="Refresh Overlay", icon='FILE_REFRESH')


_classes = (TOPOMENTOR_MT_pie,)


def register():
    for c in _classes:
        bpy.utils.register_class(c)


def unregister():
    for c in reversed(_classes):
        bpy.utils.unregister_class(c)
