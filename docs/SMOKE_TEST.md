# Smoke Test Checklist — ERPACC Refactoring

Chạy thủ công sau mỗi phase để đảm bảo không regression.

## Môi trường
- [ ] `python run.py` hoặc `flask run` khởi động không lỗi
- [ ] Truy cập `http://localhost:5000` hiển thị trang đăng nhập
- [ ] Đăng nhập admin thành công, vào dashboard

## Kịch bản 1: Phiếu nhập kho (StockIn)
- [ ] Vào **Kho > Phiếu nhập** (`/stock_in`)
- [ ] Tạo phiếu nhập mới: chọn kho, nhà cung cấp, thêm 2–3 sản phẩm
- [ ] Lưu nháp — kiểm tra trạng thái `draft`
- [ ] Xác nhận phiếu (`confirm`) — không báo lỗi
- [ ] Kiểm tra **Tồn kho**: số lượng sản phẩm tăng đúng
- [ ] Kiểm tra **Bút toán kế toán**: bút toán nhập kho tồn tại
- [ ] Kiểm tra **Công nợ**: công nợ nhà cung cấp tạo đúng
- [ ] Kiểm tra **VAT**: bản ghi VAT đầu vào tồn tại
- [ ] Hủy phiếu (`cancel`) — kiểm tra số lượng tồn kho giảm về, bút toán nghịch đảo

## Kịch bản 2: Phiếu xuất kho (StockOut)
- [ ] Vào **Kho > Phiếu xuất** (`/stock_out`)
- [ ] Tạo phiếu xuất, xác nhận
- [ ] Kiểm tra tồn kho giảm đúng
- [ ] Hủy phiếu — kiểm tra rollback

## Kịch bản 3: Báo cáo
- [ ] Vào **Báo cáo > Tổng quan** (`/reports`)
- [ ] Xuất Excel báo cáo kho — file tải về không lỗi
- [ ] Xuất PDF — không lỗi font

## Kịch bản 4: Ecommerce / Shop
- [ ] Vào `/shop` — trang cửa hàng hiển thị
- [ ] Thêm sản phẩm vào giỏ, checkout
- [ ] Kiểm tra đơn hàng trong admin

## Kịch bản 5: Settings
- [ ] Vào **Cài đặt** — các tab (users, menus, system, backup) load bình thường
- [ ] Tạo user mới, phân quyền — đăng nhập user mới thành công

## Tiêu chí pass
- Không exception trong console/server log
- Không lỗi 500 trong trình duyệt
- 4 bảng quan trọng (inventory, journal, debt, vat) cập nhật đúng sau confirm
