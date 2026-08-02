# Hướng dẫn tích hợp Google OAuth 2.0

## 1. Cài đặt thư viện

```bash
pip install authlib flask-login requests
```

---

## 2. Đăng ký Google OAuth App

1. Vào [console.cloud.google.com](https://console.cloud.google.com)
2. Tạo project mới (hoặc dùng project hiện có)
3. **APIs & Services → OAuth consent screen** → External → điền tên app, email
4. **APIs & Services → Credentials → Create Credentials → OAuth 2.0 Client ID**
   - Application type: **Web application**
   - Authorized redirect URIs: `https://yourdomain.com/shop/auth/google/callback`
   - (Local dev): `http://localhost:5000/shop/auth/google/callback`
5. Lưu lại **Client ID** và **Client Secret**

---

## 3. Cấu hình Flask (.env hoặc config)

```python
# config.py hoặc .env
GOOGLE_CLIENT_ID     = "xxxx.apps.googleusercontent.com"
GOOGLE_CLIENT_SECRET = "GOCSPX-xxxxxxxxxxxx"
GOOGLE_REDIRECT_URI  = "http://localhost:5000/shop/auth/google/callback"
SECRET_KEY           = "your-secret-key-here"
```

---

## 4. Routes cần thêm vào shop/views.py (hoặc auth blueprint)

```python
from authlib.integrations.flask_client import OAuth
import secrets, requests as req

oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=app.config['GOOGLE_CLIENT_ID'],
    client_secret=app.config['GOOGLE_CLIENT_SECRET'],
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'},
)

@shop.route('/auth/google/login')
def google_login():
    """Redirect to Google login."""
    nonce = secrets.token_urlsafe(16)
    session['google_nonce'] = nonce
    redirect_uri = url_for('shop.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)

@shop.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback."""
    try:
        token = google.authorize_access_token()
        user_info = google.parse_id_token(token, nonce=session.pop('google_nonce', None))
    except Exception as e:
        flash('Đăng nhập Google thất bại. Vui lòng thử lại.', 'danger')
        return redirect(url_for('shop.login'))

    google_id  = user_info['sub']
    email      = user_info['email']
    name       = user_info.get('name', '')
    avatar_url = user_info.get('picture', '')

    # Tìm hoặc tạo user
    user = WebCustomer.query.filter_by(google_id=google_id).first()
    if not user:
        user = WebCustomer.query.filter_by(email=email).first()
        if user:
            # Liên kết Google vào tài khoản email đã có
            user.google_id = google_id
            user.avatar_url = avatar_url or user.avatar_url
        else:
            # Tạo tài khoản mới
            user = WebCustomer(
                email=email, name=name,
                google_id=google_id, avatar_url=avatar_url,
                is_active=True,
            )
            db.session.add(user)
    db.session.commit()

    login_user(user)
    flash(f'Chào mừng {user.name}! Đăng nhập bằng Google thành công.', 'success')
    return redirect(request.args.get('next') or url_for('shop.catalog'))

@shop.route('/account/link/google')
@login_required
def link_google():
    """Link Google to existing account."""
    nonce = secrets.token_urlsafe(16)
    session['google_nonce'] = nonce
    session['linking_google'] = True
    redirect_uri = url_for('shop.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri, nonce=nonce)

@shop.route('/account/unlink/google', methods=['POST'])
@login_required
def unlink_google():
    """Unlink Google from account."""
    if not current_user.password_hash:
        flash('Hãy đặt mật khẩu trước khi huỷ liên kết Google.', 'warning')
        return redirect(url_for('shop.account'))
    current_user.google_id = None
    current_user.avatar_url = None
    db.session.commit()
    flash('Đã huỷ liên kết tài khoản Google.', 'success')
    return redirect(url_for('shop.account'))
```

---

## 5. Cột cần thêm vào model WebCustomer

```python
class WebCustomer(db.Model):
    # ... các cột hiện có ...
    google_id   = db.Column(db.String(64), unique=True, nullable=True, index=True)
    avatar_url  = db.Column(db.String(512), nullable=True)
    tier        = db.Column(db.String(20), default='member')  # member / silver / gold
    company_name = db.Column(db.String(200), nullable=True)
    tax_code    = db.Column(db.String(20), nullable=True)
```

Migration:
```bash
flask db migrate -m "add google oauth fields"
flask db upgrade
```

---

## 6. Route account page

```python
@shop.route('/account')
@login_required
def account():
    orders    = Order.query.filter_by(customer_id=current_user.id)\
                    .order_by(Order.created_at.desc()).limit(20).all()
    wishlist  = current_user.wishlist_listings  # nhiều-nhiều relationship
    addresses = current_user.addresses
    pending_orders = sum(1 for o in orders if o.status == 'pending')
    return render_template('shop/account.html',
        orders=orders, wishlist=wishlist,
        addresses=addresses, pending_orders=pending_orders)

@shop.route('/account/profile', methods=['POST'])
@login_required
def update_profile():
    current_user.name         = request.form.get('name', '').strip()
    current_user.phone        = request.form.get('phone', '').strip()
    current_user.company_name = request.form.get('company_name', '').strip()
    current_user.tax_code     = request.form.get('tax_code', '').strip()
    db.session.commit()
    flash('Đã cập nhật thông tin.', 'success')
    return redirect(url_for('shop.account'))

@shop.route('/account/password', methods=['POST'])
@login_required
def change_password():
    cur = request.form.get('current_password', '')
    new = request.form.get('new_password', '')
    confirm = request.form.get('confirm_password', '')
    if not current_user.check_password(cur):
        flash('Mật khẩu hiện tại không đúng.', 'danger')
    elif new != confirm:
        flash('Mật khẩu xác nhận không khớp.', 'danger')
    elif len(new) < 8:
        flash('Mật khẩu mới tối thiểu 8 ký tự.', 'danger')
    else:
        current_user.set_password(new)
        db.session.commit()
        flash('Đổi mật khẩu thành công!', 'success')
    return redirect(url_for('shop.account'))
```

---

## 7. Tóm tắt files đã thay đổi

| File | Thay đổi |
|------|----------|
| `base.html` | User dropdown với avatar, menu account/orders/wishlist/logout |
| `login.html` | Nút "Tiếp tục với Google" chuẩn OAuth |
| `register.html` | Nút "Đăng ký với Google" |
| `account.html` | **File mới** — Order history, Wishlist, Profile, Addresses, Security + Link Google |
| `baseshop.css` | Styles cho dropdown, account page, auth pages |

