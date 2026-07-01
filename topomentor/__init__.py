# TopoMentor - Mesh Topology Mentor
# Add-on học modeling: soi topology, chấm Health Score, chọn/vẽ geometry lỗi để sửa tay.
#
# Hỗ trợ 2 kiểu cài:
#   - Extension (Blender 4.2+): dùng blender_manifest.toml (bl_info bên dưới bị bỏ qua, vô hại).
#   - Legacy add-on (4.0/4.1): dùng bl_info này.

bl_info = {
    "name": "TopoMentor",
    "author": "byedash",
    "version": (2, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > Sidebar (N) > TopoMentor",
    "description": "Phân tích topology, chấm Health Score, overlay poles/ngon, symmetry check, sửa tay.",
    "category": "Mesh",
}

import importlib
from . import properties, topo_utils, overlay, operators, panels

# Reload sạch khi phát triển (F3 > Reload Scripts).
for _m in (properties, topo_utils, overlay, operators, panels):
    importlib.reload(_m)

# Thứ tự register:
#   properties (PropertyGroup phải có trước PointerProperty)
#   -> overlay (chuẩn bị draw handler, chưa bật)
#   -> operators -> panels.
_ordered = (properties, overlay, operators, panels)


def register():
    for m in _ordered:
        m.register()


def unregister():
    # Ngược thứ tự; overlay.unregister() sẽ gỡ draw handler để tránh leak.
    for m in reversed(_ordered):
        m.unregister()


if __name__ == "__main__":
    register()
