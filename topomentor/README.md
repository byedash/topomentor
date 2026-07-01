# TopoMentor

Add-on Blender học 3D modeling qua việc **soi và sửa topology bằng tay**.
Nó không model hộ bạn — nó chỉ ra ngon, poles, non-manifold, chấm điểm, rồi để bạn tự sửa.

## Cài đặt
### Blender 4.2+ (Extension)
`Edit > Preferences > Get Extensions > ▾ > Install from Disk…` → chọn `topomentor.zip`.

### Blender 4.0 / 4.1 (Legacy)
`Edit > Preferences > Add-ons > Install…` → chọn `topomentor.zip` → tick bật **TopoMentor**.

Mở viewport → phím **N** → tab **TopoMentor**.

## Dùng
1. Chọn 1 mesh → **Analyze Topology**.
2. Xem Health Score + số liệu.
3. **Select & Fix**: bấm N-gons/Tris/Poles/Non-manifold → vào Edit Mode, sửa tay (`F`, `J`, Grid Fill, Knife…).
4. **Overlay**: tick Show Overlay để thấy chấm màu poles/ngon trên viewport; Refresh sau khi sửa.
5. **Symmetry & Report**: kiểm tra đối xứng theo trục, xuất báo cáo .txt.

## Module
| File | Vai trò |
|------|---------|
| `topo_utils.py` | Logic numpy/bmesh thuần (không UI) |
| `properties.py` | PropertyGroup gắn vào Scene |
| `overlay.py` | GPU draw handler |
| `operators.py` | Hành động (analyze/select/fix/export) |
| `panels.py` | UI N-panel |

Version 2.0.0 — Blender 4.x/5.x.
