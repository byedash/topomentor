# TopoMentor - Mesh Topology Mentor
# Add-on hoc modeling: soi topology, cham Health Score, overlay/HUD, popup, pie menu.
#
# Ho tro 2 kieu cai:
#   - Extension (Blender 4.2+): dung blender_manifest.toml (bl_info duoi bi bo qua, vo hai).
#   - Legacy add-on (4.0/4.1): dung bl_info nay.

bl_info = {
    "name": "TopoMentor",
    "author": "byedash",
    "version": (3, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar (N) > TopoMentor | Pie: Alt+X",
    "description": "Phan tich topology, Health Score, overlay/HUD, popup setup/cleanup/symmetrize, pie menu.",
    "category": "Mesh",
}

import importlib
from . import properties, topo_utils, overlay, operators, menus, panels, keymaps

for _m in (properties, topo_utils, overlay, operators, menus, panels, keymaps):
    importlib.reload(_m)

# Thu tu register:
#   properties (PropertyGroup truoc PointerProperty)
#   -> overlay -> operators -> menus -> panels -> keymaps (can operators+menu da co).
_ordered = (properties, overlay, operators, menus, panels, keymaps)


def register():
    for m in _ordered:
        m.register()


def unregister():
    # Nguoc thu tu; overlay/keymaps se go handler + keymap de tranh leak.
    for m in reversed(_ordered):
        m.unregister()


if __name__ == "__main__":
    register()
