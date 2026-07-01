# Keymap: gan pie menu vao Alt+X trong 3D View.
# Luu (km, kmi) de go dung cai minh them khi unregister.

import bpy

_addon_keymaps = []


def register():
    wm = bpy.context.window_manager
    kc = wm.keyconfigs.addon           # keyconfig danh rieng cho add-on
    if kc is None:
        return                         # chay headless/background thi khong co
    km = kc.keymaps.new(name='3D View', space_type='VIEW_3D')
    kmi = km.keymap_items.new('wm.call_menu_pie', 'X', 'PRESS', alt=True)
    kmi.properties.name = 'TOPOMENTOR_MT_pie'
    _addon_keymaps.append((km, kmi))


def unregister():
    for km, kmi in _addon_keymaps:
        try:
            km.keymap_items.remove(kmi)
        except Exception:
            pass
    _addon_keymaps.clear()
