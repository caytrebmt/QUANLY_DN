# Phân quyền & Menu — ERPACC

Tài liệu này mô tả cơ chế phân quyền và hiển thị menu của ERPACC sau đợt tối ưu
(đồng bộ menu ↔ nghiệp vụ, chuẩn hóa vai trò, gỡ bỏ phân quyền vai trò cứng).

## 1. Tổng quan

Hệ thống dùng **một nguồn chân lý duy nhất** cho phân quyền:
hiển thị menu và truy cập route đều dựa trên **quyền theo module** của từng user.

```
Menu hiển thị  ──▶ current_user.has_permission(module, 'view')
Route bảo vệ  ──▶ @require_permission(module, action)
                     ↓
              UserPermission (bảng) + UserPermission.DEFAULT_ROLE_PERMS (mặc định)
```

Vì cả hai cùng dùng `has_permission`, **menu nào hiển thị thì route tương ứng
luôn cho qua**, và ngược lại — không còn tình trạng "thấy menu mà bị chặn".

## 2. Vai trò (Roles)

Tập vai trò được chuẩn hóa tại `app/shared/constants/__init__.py` (class `Roles`):

| Hằng | Giá trị | Mô tả |
|------|--------|-------|
| `ADMIN` | `admin` | Quản trị viên — luôn có mọi quyền |
| `ACCOUNTANT` | `accountant` | Kế toán |
| `WAREHOUSE` | `warehouse` | Thủ kho |
| `USER` | `user` | Người dùng nội bộ |
| `WEB_CUSTOMER` | `web_customer` | Khách hàng web (shop) |
| `ERP_USER` | `erp_user` | Nhân viên ERP (shop) |

- `Roles.INTERNAL` = `{admin, accountant, warehouse, user}` — các vai trò nội bộ.
- `Roles.is_valid(role)` / `Roles.normalize(role)` dùng khi tạo/sửa user để **không
  chấp nhận vai trò tự do** (tránh user "tàng hình" không vào được route nào).
- `User.role` mặc định = `Roles.USER`.

## 3. Quyền theo module (UserPermission)

Bảng `user_permissions` (`app/models/system.py`):

```
user_id | module | can_view | can_add | can_edit | can_delete
```

`User.has_permission(module, action)` ánh xạ action → trường:

| action | trường |
|--------|--------|
| view / export | `can_view` |
| add / create | `can_add` |
| edit / update / confirm | `can_edit` |
| delete / remove | `can_delete` |

Logic:
1. Admin → luôn `True`.
2. Có bản ghi `UserPermission` cho module → dùng giá trị cột.
3. Không có bản ghi → dùng `DEFAULT_ROLE_PERMS[role][module]` (quyền mặc định theo vai trò).

`DEFAULT_ROLE_PERMS` định nghĩa sẵn quyền mặc định cho `user` / `warehouse` / `accountant`.
Khi admin tạo/sửa user qua form "Quản lý users", các checkbox quyền được ghi vào
`user_permissions` (với admin thì full quyền bất kể form).

## 4. Bảo vệ route

`app/shared/authz/__init__.py` chỉ còn `require_permission(module, action='view')`:

```python
@stock_out_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('stock_out', 'create')
def create(): ...
```

- Chưa đăng nhập → chuyển `auth.login`.
- Không đủ quyền → flash cảnh báo, về `dashboard.index`.
- Decorator `require_roles(...)` đã **xóa bỏ** (trùng lặp với `require_permission`,
  và gây lệch quyền cứng). Mọi route trước dùng `require_roles` đều đã chuyển sang
  `require_permission` tương ứng — quyền hiệu dụng không đổi.

## 5. Hiển thị menu

Hàm `_get_nav_menus(role, user_id)` (`app/core/__init__.py`) quyết định menu sidebar:

1. **`UserMenuOverride`** (bảng `user_menu_overrides`) — cao nhất, ghi đè từng user
   (ẩn/hiện một menu cụ thể). Thiết lập tại "Quản lý users → Menu hiển thị".
2. **Module + quyền xem** — menu có `module` → hiển thị nếu
   `current_user.has_permission(menu.module, 'view')`.
3. Menu **không gắn module** → chỉ `admin` thấy.

Cache: kết quả được cache 300s theo `nav_menus:{role}:{user_id}`.

### Cache invalidation (tự động)

Listener `after_commit` trong `create_app` tự gọi `invalidate_nav_cache()` khi một
trong các bảng sau thay đổi: `menus`, `user_menu_overrides`, `users`,
`user_permissions`. Không cần gọi thủ công ở từng route (các lời gọi cũ vẫn vô hại).

## 6. Cấu hình menu (UI)

Tại **Cài đặt → Cấu hình menu**:

- **Module chức năng** (bắt buộc): quyết định ai thấy menu. Để trống → chỉ Admin.
- Hiển thị menu = tự động suy ra từ Module + quyền user. **Không chọn vai trò tại form này**.
- Tab "Xem trước (mặc định theo vai trò)": xem menu mà mỗi vai trò thấy theo
  `DEFAULT_ROLE_PERMS` (quyền mặc định). Quyền thực tế của từng user có thể khác
  (tùy chỉnh tại Quản lý users).
- Ẩn/hiện riêng từng user: **Quản lý users → Menu hiển thị** (`UserMenuOverride`).

## 7. Thành phần đã loại bỏ / cũ (deprecated)

| Thành phần | Trạng thái |
|------------|-----------|
| `require_roles()` | Đã xóa. Thay bằng `require_permission`. |
| `MenuRole` (bảng `menu_roles`) | **Không còn dùng** để quyết định hiển thị. Vẫn tồn tại trong schema (không cần migration) nhưng runtime không ghi/đọc. Bootstrap seed vẫn tạo để tương thích. |
| `Menu.roles` (CSV) | Không còn dùng cho visibility. Giữ lại cột DB để không phá schema. |
| Chọn vai trò trong form menu | Đã gỡ khỏi UI. |

> Lưu ý: nếu sau này muốn xóa hẳn bảng `menu_roles` và cột `roles`, cần tạo
> migration Alembic mới (không thay đổi schema inline).

## 8. Quy trình thay đổi quyền (nhanh)

1. Thêm/sửa module mới → thêm vào `UserPermission.MODULES` và (nếu muốn quyền mặc
   định) vào `DEFAULT_ROLE_PERMS`.
2. Bảo vệ route mới → `@require_permission('module', 'action')`.
3. Thêm menu mới → gán đúng `module` (khớp tên module ở bước 1).
4. Gán quyền riêng cho user → "Quản lý users".
5. Cache tự làm mới sau commit; không cần restart.

## 9. Kiểm tra nhanh

- User `accountant` có thấy menu "Kế toán"? → Có, vì `DEFAULT_ROLE_PERMS['accountant']['accounting']['can_view'] = True`.
- User `user` có thấy menu "Phiếu nhập kho"? → Không, `warehouse`/`accountant` mới có.
- Admin sửa quyền user X tắt "Kế toán" → menu "Kế toán" biến khỏi sidebar X ngay sau commit.
- Gán `UserMenuOverride` ẩn menu X cho user Y → menu X biến khỏi sidebar Y dù Y có quyền module.
