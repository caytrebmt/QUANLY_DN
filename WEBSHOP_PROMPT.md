# Prompt hoàn chỉnh: Xây dựng WebShop SPA tích hợp ERPACC

Bạn là fullstack developer. Hãy xây dựng một **React SPA webshop bán hàng hoàn chỉnh** tích hợp trực tiếp với hệ thống ERPACC backend đã có sẵn.

---

## 1. Tổng quan hệ thốngc

### Backend ERPACC (đã sẵn sàng)
- **Base URL**: `http://localhost:5000` (dev) hoặc domain production
- **API Shop**: Tất cả endpoints dưới `/api/shop/*`
- **Auth**: JWT Bearer token trong header `Authorization: Bearer <access_token>`
- **Database**: PostgreSQL, chứa products, customers, orders, cart, promotions
- **CSRF**: Đã exempt toàn bộ `/api/shop/*`
- **CORS**: Đã cấu hình, cho phép origin khác gọi API

### Tech Stack yêu cầu
- **Frontend**: React 18+ với Vite
- **State Management**: React Context + useReducer (không cần Redux)
- **Routing**: React Router v6
- **HTTP Client**: Axios với interceptor cho JWT refresh
- **UI**: Tailwind CSS + shadcn/ui components
- **Icons**: Lucide React
- **Form**: React Hook Form + Zod validation
- **Build**: Vite, output vào `dist/` để deploy

---

## 2. API Endpoints đã sẵn sàng

### Auth
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| POST | `/api/shop/auth/login` | Đăng nhập, trả `{ok, data: {access_token, refresh_token, customer}}` |
| POST | `/api/shop/auth/register` | Đăng ký, trả `{ok, data: {access_token, refresh_token, customer}}` |
| POST | `/api/shop/auth/refresh` | Làm mới token, header `Authorization: Bearer <refresh_token>` |

### Catalog
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/shop/catalog` | Danh sách SP, query params: `search`, `category_id`, `page`, `per_page` |
| GET | `/api/shop/categories` | Danh sách danh mục `{categories: [{id, code, name}]}` |
| GET | `/api/shop/products/:id` | Chi tiết SP `{ok, data: {id, sku, name, description, imageUrl, salePrice, stock, categoryId, unit, slug}}` |

### Cart
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/shop/cart` | Giỏ hàng `{ok, data: {cart_id, items, subtotal, total, item_count}}` |
| POST | `/api/shop/cart/items` | Thêm vào giỏ `{listing_id?, product_id?, quantity}` |
| PUT | `/api/shop/cart/items/:id` | Cập nhật số lượng `{quantity}` |
| DELETE | `/api/shop/cart/items/:id` | Xóa item |
| DELETE | `/api/shop/cart` | Xóa toàn bộ giỏ |

### Orders
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/shop/orders` | Lịch sử đơn `{ok, data: {items, total, page, pages}}` |
| GET | `/api/shop/orders/:code` | Chi tiết đơn `{ok, data: {code, status, items, total_amount, ...}}` |
| POST | `/api/shop/orders` | Tạo đơn `{customerName, shippingAddress, paymentMethod, items?}` |
| POST | `/api/shop/orders/:id/reorder` | Mua lại đơn cũ |
| POST | `/api/shop/orders/:id/cancel` | Hủy đơn (chỉ được hủy khi status=new) |

### Customer
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/shop/customer/profile` | Thông tin tài khoản |
| PUT | `/api/shop/customer/profile` | Cập nhật `{name, phone, email?}` |
| PUT | `/api/shop/customer/password` | Đổi mật khẩu `{current_password, new_password, confirm_password}` |

### Promotions
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/shop/promotions` | Danh sách KM đang active |
| POST | `/api/shop/promotions/validate` | Kiểm tra mã `{code, amount}` → `{discount_amount}` |

### Legacy (backward compatible)
| Method | Endpoint | Mô tả |
|--------|----------|-------|
| GET | `/api/shop/catalog` | Legacy catalog, trả `{products: [], categories: [], brands: []}` |
| POST | `/api/shop/checkout-json` | Legacy checkout |

---

## 3. Response Format chuẩn

Tất cả API trả về format:
```json
{
  "ok": true/false,
  "data": { ... },
  "message": "string"
}
```

Status codes:
- `200`: Success
- `400`: Bad request (thiếu field, validation fail)
- `401`: Unauthorized (token expired/invalid)
- `404`: Not found
- `409`: Conflict (email đã tồn tại)

---

## 4. Cấu trúc dự án React

```
webshop/
├── src/
│   ├── api/
│   │   └── client.ts          # Axios instance + interceptors
│   ├── contexts/
│   │   ├── AuthContext.tsx    # Auth state + login/logout/register
│   │   └── CartContext.tsx    # Cart state + add/remove/update
│   ├── hooks/
│   │   ├── useAuth.ts
│   │   ├── useCart.ts
│   │   └── useProducts.ts
│   ├── pages/
│   │   ├── CatalogPage.tsx   # Trang danh sách sản phẩm
│   │   ├── ProductPage.tsx   # Trang chi tiết sản phẩm
│   │   ├── CartPage.tsx      # Giỏ hàng
│   │   ├── CheckoutPage.tsx  # Thanh toán
│   │   ├── OrdersPage.tsx    # Lịch sử đơn hàng
│   │   ├── OrderDetailPage.tsx
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── AccountPage.tsx   # Thông tin tài khoản
│   │   └── TrackOrderPage.tsx
│   ├── components/
│   │   ├── Header.tsx        # Header với cart badge, search
│   │   ├── Footer.tsx
│   │   ├── ProductCard.tsx
│   │   ├── CartItem.tsx
│   │   ├── OrderItem.tsx
│   │   ├── CategoryNav.tsx
│   │   ├── ProtectedRoute.tsx
│   │   └── PromoBanner.tsx
│   ├── layouts/
│   │   └── ShopLayout.tsx    # Layout chung với Header/Footer
│   ├── utils/
│   │   ├── format.ts         # formatPrice, formatDate
│   │   └── storage.ts        # localStorage helpers
│   ├── App.tsx
│   ├── main.tsx
│   └── index.css
├── public/
│   └── placeholder.svg       # SVG placeholder cho sản phẩm không có ảnh
├── package.json
├── vite.config.ts
├── tailwind.config.ts
└── tsconfig.json
```

---

## 5. Yêu cầu chi tiết từng trang

### 5.1 Catalog Page (`/`)
- Grid sản phẩm, mỗi card: ảnh, tên, giá, tồn kho, nút "Thêm vào giỏ"
- Sidebar/top bar: filter theo category, search box
- Pagination: load more / infinite scroll hoặc page numbers
- Responsive: mobile 1 col, tablet 2 col, desktop 3-4 col
- Skeleton loading khi đang fetch
- Badge "Hết hàng" khi stock <= 0

### 5.2 Product Detail (`/product/:slug`)
- Ảnh lớn, tên, giá, mô tả, tồn kho
- Nút "Thêm vào giỏ" với selector số lượng
- Tab: Mô tả | Thông số
- Sản phẩm liên quan (cùng category)
- Breadcrumb: Trang chủ > Danh mục > Sản phẩm

### 5.3 Cart Page (`/cart`)
- Danh sách items: ảnh, tên, đơn giá, số lượng (+/-), thành tiền
- Tổng cộng
- Nút "Tiến hành thanh toán"
- Nút "Xóa" từng item
- Empty state khi giỏ trống

### 5.4 Checkout Page (`/checkout`)
- Form: Họ tên, SĐT, Địa chỉ giao hàng
- Chọn phương thức thanh toán: COD / VietQR / Bank transfer
- Nhập mã khuyến mãi (gọi `/api/shop/promotions/validate`)
- Tóm tắt đơn hàng
- Nút "Đặt hàng" → gọi `/api/shop/orders` POST
- Redirect về `/order-success/:code`

### 5.5 Orders List (`/orders`)
- Protected route (cần đăng nhập)
- Danh sách đơn: mã đơn, ngày, tổng tiền, trạng thái
- Badge màu theo status: new (xanh), pending (vàng), confirmed (xanh lá), cancelled (đỏ)
- Click vào xem chi tiết `/orders/:code`

### 5.6 Login/Register
- Form đăng nhập: email + password
- Form đăng ký: họ tên, email, phone, password, confirm password
- Validation: password >= 8 chars, email hợp lệ
- Sau khi đăng nhập/đăng ký: lưu tokens vào localStorage, redirect về trang trước
- Nút "Quên mật khẩu?" → hiển thị thông báo liên hệ admin (chưa cần implement reset)

### 5.7 Account Page (`/account`)
- Protected route
- Thông tin profile: tên, email, phone (có thể edit)
- Form đổi mật khẩu
- Link đến lịch sử đơn hàng
- Nút đăng xuất

---

## 6. Luồng dữ liệu chính

```
1. User truy cập webshop
   ↓
2. React app load → fetch /api/shop/catalog + /api/shop/categories
   ↓
3. User browse/search sản phẩm
   ↓
4. User thêm vào giỏ → POST /api/shop/cart/items
   → Backend tạo CustomerSession + Cart (nếu chưa có)
   → Trả về cart data
   ↓
5. User checkout:
   a. Nếu chưa đăng nhập → tạo đơn dạng guest (customer_name, shipping_address)
   b. Nếu đã đăng nhập → JWT token trong header
      → Backend link với WebCustomer + ERP Customer
   ↓
6. Đơn hàng được lưu vào bảng online_orders
   → ERP admin có thể xem và sync sang StockOut
```

---

## 7. Auth Flow chi tiết

```typescript
// Login
POST /api/shop/auth/login
Body: { email, password }
Response: { ok, data: { access_token, refresh_token, customer } }

// Store tokens
localStorage.setItem('access_token', data.access_token)
localStorage.setItem('refresh_token', data.refresh_token)
localStorage.setItem('current_user', JSON.stringify(data.customer))

// Axios interceptor
request.headers.Authorization = `Bearer ${access_token}`

// Auto refresh khi 401
if (response.status === 401 && refreshToken) {
  const newToken = await refreshAccessToken()
  retry request with new token
}

// Refresh endpoint
POST /api/shop/auth/refresh
Header: Authorization: Bearer <refresh_token>
Response: { ok, data: { access_token } }
```

---

## 8. UI/UX Requirements

### Design System
- **Màu chủ đạo**: Xanh đậm `#0f3b2c`, Cam nhạt `#d4a373`
- **Font**: System font stack (-apple-system, Segoe UI, Roboto)
- **Radius**: 8px cho cards, 4px cho buttons
- **Shadow**: nhẹ `0 2px 4px rgba(0,0,0,0.1)`

### Responsive Breakpoints
- Mobile: < 640px (1 col)
- Tablet: 640px - 1024px (2 col)
- Desktop: > 1024px (3-4 col)

### Loading States
- Skeleton cho product cards
- Spinner cho cart/checkout
- Toast notification cho success/error

### Toast Notifications
- Success: xanh lá, icon check
- Error: đỏ, icon X
- Info: xanh dương, icon info
- Auto dismiss sau 3s

---

## 9. Build & Deploy

### Development
```bash
npm install
npm run dev        # Vite dev server trên port 5173
```

### Production Build
```bash
npm run build      # Output vào /dist
```

### Deploy Options
**Option A**: Build vào `app/static/shop/` rồi Flask serve (giống shop hiện tại)
**Option B**: Deploy riêng trên Vercel/Netlify, proxy API qua Nginx/CORS
**Option C**: Build vào `/dist` và serve bằng Waitress/Gunicorn static files

### Nginx config (nếu deploy riêng)
```nginx
server {
    listen 80;
    server_name shop.erpviet.com;
    
    # React static files
    root /path/to/webshop/dist;
    try_files $uri $uri/ /index.html;
    
    # Proxy API về ERP
    location /api/shop/ {
        proxy_pass http://localhost:5000/api/shop/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 10. Data Flow Example

### Thêm vào giỏ hàng
```typescript
// 1. User click "Thêm vào giỏ"
// 2. Gọi API
POST /api/shop/cart/items
Header: Authorization: Bearer <token>
Body: { listing_id: 110, quantity: 2 }

// 3. Response
{
  "ok": true,
  "data": {
    "cart_id": 15,
    "items": [{ "id": 51, "name": "Giấy A4", "unit_price": 35000, "quantity": 2, "amount": 70000 }],
    "subtotal": 70000,
    "total": 70000,
    "item_count": 1
  }
}

// 4. Update cart badge trong Header
```

### Tạo đơn hàng
```typescript
// 1. User submit checkout form
// 2. Gọi API
POST /api/shop/orders
Header: Authorization: Bearer <token>
Body: {
  "customerName": "Nguyen Van A",
  "customerPhone": "0909123456",
  "customerEmail": "a@example.com",
  "shippingAddress": "123 Nguyen Van Troi, Q.1, HCMC",
  "paymentMethod": "COD",
  "note": "Gọi trước khi giao"
}

// 3. Response
{
  "ok": true,
  "data": {
    "order": {
      "code": "WEB-260716-0012",
      "status": "new",
      "total_amount": 192500,
      "items": [...]
    }
  }
}

// 4. Redirect to /order-success/WEB-260716-0012
```

---

## 11. Lưu ý quan trọng

1. **Token storage**: Lưu access_token + refresh_token trong localStorage
2. **Auto refresh**: Interceptor tự động refresh khi 401, retry request
3. **Guest cart**: Cho phép thêm giỏ hàng mà không đăng nhập (dùng session)
4. **Guest checkout**: Cho phép đặt hàng mà không đăng nhập (chỉ cần name/address/phone)
5. **Stock check**: Nếu product.stock <= 0 thì disable nút "Thêm vào giỏ", hiển thị "Hết hàng"
6. **Image fallback**: Nếu product không có ảnh thì dùng placeholder SVG
7. **Category sync**: Categories load từ ERP, không hardcode
8. **Price format**: VND, dùng `Intl.NumberFormat('vi-VN')`

---

## 12. Testing Checklist

- [ ] Đăng ký tài khoản mới → Tạo được WebCustomer + ERP Customer
- [ ] Đăng nhập → Nhận JWT token
- [ ] Xem danh sách sản phẩm → Data từ ERP realtime
- [ ] Search sản phẩm → Filter theo tên/mã
- [ ] Thêm vào giỏ → Cart tạo/update đúng
- [ ] Cập nhật số lượng → PUT /cart/items/:id
- [ ] Checkout → Tạo đơn hàng, order có customer_id ERP
- [ ] Xem lịch sử đơn → GET /orders
- [ ] Cập nhật profile → Sync lên ERP Customer
- [ ] Đổi mật khẩu → Thành công
- [ ] Refresh token → Tự động làm mới access_token
- [ ] Logout → Xóa tokens, redirect về catalog

---

## 13. Không cần làm

- Quản lý sản phẩm/thêm/sửa/xóa (đã có trong ERP admin)
- Quản lý danh mục (đã có trong ERP admin)
- Quản lý đơn hàng admin (đã có trong ERP admin)
- Payment gateway integration (chỉ hiển thị methods)
- Email notification (có thể để placeholder)

---

Hãy bắt đầu với việc khởi tạo React project bằng Vite + TypeScript, setup routing, auth context, và build từng trang theo thứ tự ưu tiên: Catalog → Product Detail → Cart → Checkout → Orders → Account.
