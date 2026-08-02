from itertools import product

from flask import (Blueprint, current_app, render_template, request, redirect,
                   url_for, flash, send_file, jsonify)
from flask_login import login_required, current_user
from app.database import db
from app.domains.master.models import Product, Unit, Category, ProductImage

from app.shared.export.excel_exporter import ExcelExporter
from app.shared.export.excel_importer import ExcelImporter
from app.shared.authz import require_permission
import io, os, uuid, pandas as pd
from datetime import datetime
import re
import math
import unicodedata
from PIL import Image, ImageOps
from werkzeug.utils import secure_filename
from app.domains.master.services.product_code_service import (
    generate_product_code,
    slug_code_from_name,
    generate_unique_code,
)

products_bp = Blueprint('products', __name__, url_prefix='/products')

_IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp', '.gif'}
_COMPRESSED_EXT = '.jpg'


def _save_product_image(upload, product):
    if not upload or not upload.filename:
        return None
    _, ext = os.path.splitext(
        secure_filename(upload.filename).lower()
    )
    if ext not in _IMAGE_EXTENSIONS:
        flash(
            'Ảnh sản phẩm chỉ hỗ trợ JPG, PNG, WEBP hoặc GIF.',
            'warning'
        )
        return None

    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], 'products')

    os.makedirs(upload_dir, exist_ok=True)

    image_count = ProductImage.query.filter_by(product_id=product.id).count()

    filename = (f"{secure_filename(product.code.upper())}_"
                f"{image_count + 1}"
                f"{_COMPRESSED_EXT}"
                )

    target_path = os.path.join(upload_dir, filename)
    max_px = int(current_app.config.get('PRODUCT_IMAGE_MAX_PX', 1600))
    quality = int(current_app.config.get('PRODUCT_IMAGE_QUALITY', 82))

    try:
        img = Image.open(upload.stream)
        img = ImageOps.exif_transpose(img)
        img.thumbnail((max_px, max_px), Image.Resampling.LANCZOS)

        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGBA')
            bg = Image.new('RGB', img.size, (255, 255, 255))
            bg.paste(img, mask=img.getchannel('A'))
            img = bg
        else:
            img = img.convert('RGB')
        img.save(target_path, 'JPEG',
                 quality=quality,
                 optimize=True,
                 progressive=True
                 )

    except Exception:
        flash('Không thể xử lý ảnh. Vui lòng thử file khác.', 'warning')
        return None
    return url_for(
        'static',
        filename=f'uploads/products/{filename}'
    )


def _add_product_image(product, upload):

    image_url = _save_product_image(upload, product)
    if not image_url:
        return None

    next_order = (ProductImage.query.filter_by(product_id=product.id).count()) + 1

    image = ProductImage(
        product_id=product.id,
        image_url=image_url,
        image_name=os.path.basename(image_url),
        sort_order=next_order,
        is_main=(next_order == 1)
    )

    db.session.add(image)
    return image


@products_bp.post('/image/delete/<int:image_id>')
@login_required
@require_permission('products', 'edit')
def delete_image(image_id):
    img = ProductImage.query.get_or_404(image_id)
    try:
        if img.image_url:
            rel_path = img.image_url.replace('/static/', '')
            file_path = os.path.join(current_app.static_folder, rel_path)

            if os.path.exists(file_path):
                os.remove(file_path)
        db.session.delete(img)
        db.session.commit()
        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        return jsonify({'success': False, 'message': str(e)})


def _replace_main_product_image(product, upload):
    if not upload or not upload.filename:
        return
    ProductImage.query.filter_by(product_id=product.id).update({'is_main': False})
    image_url = _save_product_image(upload, product)
    if not image_url:
        return
    next_order = (ProductImage.query.filter_by(product_id=product.id).count()) + 1
    db.session.add(
        ProductImage(
            product_id=product.id,
            image_url=image_url,
            image_name=os.path.basename(image_url),
            sort_order=next_order,
            is_main=True
        )
    )


def _normalize_text(value):
    s = unicodedata.normalize('NFD', str(value or ''))
    s = ''.join(ch for ch in s if unicodedata.category(ch) != 'Mn')
    s = s.replace('đ', 'd').replace('Đ', 'D')
    return s.casefold().strip()


class _SimplePagination:
    def __init__(self, items, page, per_page, total):
        self.items = items
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = max(1, math.ceil(total / per_page)) if total else 1

    def iter_pages(self, left_edge=1, right_edge=1, left_current=2, right_current=2):
        last = 0
        for num in range(1, self.pages + 1):
            if (
                num <= left_edge
                or (self.page - left_current - 1 < num < self.page + right_current)
                or num > self.pages - right_edge
            ):
                if last + 1 != num:
                    yield None
                yield num
                last = num


def _get_form_context():
    units = Unit.query.filter_by(is_active=True).order_by(Unit.name).all()
    categories = Category.query.filter_by(is_active=True).order_by(Category.name).all()
    from app.domains.master.models import Warehouse
    warehouses = Warehouse.query.filter_by(is_active=True).all()
    return units, categories, warehouses


@products_bp.route('/')
@login_required
@require_permission('products', 'view')
def index():
    search = request.args.get('search', '')
    category = request.args.get('category', '')
    page = request.args.get('page', 1, type=int)

    q = Product.query
    if search:
        q = q.filter(db.or_(Product.code.ilike(f'%{search}%'),
                            Product.name.ilike(f'%{search}%'),
                            Product.barcode.ilike(f'%{search}%')))
    if category:
        q = q.filter(db.or_(Product.category == category,
                            Product.cat_obj.has(name=category)))
    q = q.order_by(Product.code)
    products = q.paginate(page=page, per_page=20, error_out=False)

    if search and products.total == 0:
        base_q = Product.query
        if category:
            base_q = base_q.filter(
                db.or_(Product.category == category, Product.cat_obj.has(name=category))
            )
        rows = base_q.order_by(Product.code).all()
        needle = _normalize_text(search)
        matched = []
        for p in rows:
            haystack = " ".join([
                p.code or '',
                p.name or '',
                p.barcode or '',
                p.category or '',
            ])
            if needle in _normalize_text(haystack):
                matched.append(p)

        per_page = 20
        start = (page - 1) * per_page
        end = start + per_page
        products = _SimplePagination(
            items=matched[start:end],
            page=page,
            per_page=per_page,
            total=len(matched),
        )

    categories = db.session.query(Product.category).filter(
        Product.category.isnot(None)).distinct().all()
    categories = sorted(set([c[0] for c in categories if c[0]]))
    return render_template('products/index.html',
                           products=products, search=search,
                           category=category, categories=categories)


@products_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('products', 'create')
def create():
    units, cats, warehouses = _get_form_context()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        code = request.form.get('code', '').strip().upper()

        if not name:
            flash('Tên hàng không được để trống!', 'danger')

            return render_template(
                'products/form.html',
                product=None,
                units=units,
                categories=cats,
                warehouses=warehouses
            )

        code = generate_product_code(name=name, user_code=code)

        upload = request.files.get('image_file')

        if upload and upload.filename:
            _add_product_image(
                p,
                upload
            )

        unit_id = request.form.get('unit_id', type=int) or None
        cat_id = request.form.get('category_id', type=int) or None

        unit_name = request.form.get('unit', 'Cái')
        cat_name = request.form.get('category', '').strip()

        if unit_id:
            u = Unit.query.get(unit_id)
            if u:
                unit_name = u.name

        if cat_id:
            c = Category.query.get(cat_id)
            if c:
                cat_name = c.name

        p = Product(
            code=code,
            name=name,

            name_en=request.form.get('name_en', '').strip(),

            unit_id=unit_id,
            unit=unit_name,

            category_id=cat_id,
            category=cat_name,

            purchase_price=float(request.form.get('purchase_price', 0) or 0),
            sale_price=float(request.form.get('sale_price', 0) or 0),
            vat_rate=float(request.form.get('vat_rate', 10) or 10),
            min_stock=float(request.form.get('min_stock', 0) or 0),
            allow_negative=(request.form.get('allow_negative') == 'on'),
            description=request.form.get('description', '').strip(),
            barcode=request.form.get('barcode', '').strip(),

        )

        db.session.add(p)
        db.session.flush()

        conv_unit_ids = request.form.getlist('conv_unit_id[]')
        conv_factors = request.form.getlist('conv_factor[]')

        from app.domains.inventory.models import UnitConversion

        for u_id, f_val in zip(conv_unit_ids, conv_factors):

            if not u_id or not f_val:
                continue

            try:
                db.session.add(
                    UnitConversion(
                        product_id=p.id,
                        from_unit_id=int(u_id),
                        to_unit_id=p.unit_id,
                        conversion_factor=float(f_val)
                    )
                )

            except Exception:
                pass

        opening_wh_id = request.form.get(
            'opening_warehouse_id',
            type=int
        )

        opening_qty = float(
            request.form.get('opening_qty', 0) or 0
        )

        opening_cost = float(
            request.form.get(
                'opening_cost',
                p.purchase_price
            ) or p.purchase_price
        )

        if opening_wh_id and opening_qty > 0:
            from app.domains.inventory.services.inventory_service import InventoryService

            try:
                InventoryService.stock_in(
                    product_id=p.id,
                    warehouse_id=opening_wh_id,
                    quantity=opening_qty,
                    unit_cost=opening_cost,
                    reference_code=f'OPEN-{code}',
                    note=f'Nhập kho ban đầu khi tạo hàng hóa {code}',
                    user_id=current_user.id
                )
            except Exception as e:
                flash(
                    f'Lỗi nhập kho ban đầu: {e}',
                    'warning'
                )

        db.session.commit()

        flash(
            f'Thêm hàng hóa {code} thành công!',
            'success'
        )

        return redirect(url_for('products.index'))

    return render_template(
        'products/form.html',
        product=None,
        units=units,
        categories=cats,
        warehouses=warehouses
    )


@products_bp.route('/products/quick-create', methods=['POST'])
@login_required
@require_permission('products', 'create')
def quick_create_product():
    data = request.get_json()

    name = (data.get('name') or '').strip()
    code = (data.get('code') or '').strip().upper()

    if not name:
        return jsonify({
            'success': False,
            'message': 'Tên hàng không được để trống'
        }), 400

    code = generate_product_code(name=name, user_code=code)

    unit_id = data.get('unit_id') or None
    category_id = data.get('category_id') or None

    purchase_price = float(data.get('purchase_price') or 0)
    sale_price = float(data.get('sale_price') or 0)
    vat_rate = float(data.get('vat_rate') or 0)

    unit_name = ''
    category_name = ''

    if unit_id:
        u = Unit.query.get(unit_id)
        if u:
            unit_name = u.name

    if category_id:
        c = Category.query.get(category_id)
        if c:
            category_name = c.name

    product = Product(
        code=code,
        name=name,
        unit_id=unit_id,
        unit=unit_name,
        category_id=category_id,
        category=category_name,
        purchase_price=purchase_price,
        sale_price=sale_price,
        vat_rate=vat_rate,
        is_active=True
    )

    db.session.add(product)
    db.session.commit()

    return jsonify({
        'success': True,
        'product': {
            'id': product.id,
            'code': product.code,
            'name': product.name,
            'sale_price': float(product.sale_price or 0),
            'unit': product.unit or '',
            'unit_id': product.unit_id,
            'vat_rate': float(product.vat_rate or 0)
        }
    })


@products_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('products', 'edit')
def edit(id):
    p = Product.query.get_or_404(id)
    units, cats, warehouses = _get_form_context()
    from app.domains.inventory.models import UnitConversion
    conversions = UnitConversion.query.filter_by(product_id=p.id).all()
    if request.method == 'POST':
        p.name = request.form.get('name', '').strip()
        p.name_en = request.form.get('name_en', '').strip()
        unit_id = request.form.get('unit_id', type=int) or None
        cat_id = request.form.get('category_id', type=int) or None
        p.unit_id = unit_id
        p.category_id = cat_id
        if unit_id:
            u = Unit.query.get(unit_id)
            if u:
                p.unit = u.name
        else:
            p.unit = request.form.get('unit', p.unit)
        if cat_id:
            c = Category.query.get(cat_id)
            if c:
                p.category = c.name
        else:
            p.category = request.form.get('category', p.category or '')
        p.purchase_price = float(request.form.get('purchase_price', 0) or 0)
        p.sale_price = float(request.form.get('sale_price', 0) or 0)
        p.retail_price = float(request.form.get('retail_price', 0) or 0)
        p.contact_for_price = request.form.get('contact_for_price') == 'on'
        p.vat_rate = float(request.form.get('vat_rate', 10) or 10)

        p.min_stock = float(request.form.get('min_stock', 0) or 0)

        p.allow_negative = request.form.get('allow_negative') == 'on'
        p.description = request.form.get('description', '').strip()
        p.barcode = request.form.get('barcode', '').strip()
        upload = request.files.get('image_file')

        files = request.files.getlist('images')

        for upload in files:

            if upload and upload.filename:

                _add_product_image(
                    p,
                    upload
                )

        p.is_active = request.form.get('is_active') == 'on'
        UnitConversion.query.filter_by(product_id=p.id).delete()
        conv_unit_ids = request.form.getlist('conv_unit_id[]')
        conv_factors = request.form.getlist('conv_factor[]')
        for u_id, f_val in zip(conv_unit_ids, conv_factors):
            if not u_id or not f_val:
                continue
            try:
                db.session.add(UnitConversion(
                    product_id=p.id,
                    from_unit_id=int(u_id),
                    to_unit_id=p.unit_id,
                    conversion_factor=float(f_val)
                ))
            except Exception:
                pass

        db.session.commit()
        flash(f'Cập nhật hàng hóa {p.code} thành công!', 'success')
        return redirect(url_for('products.index'))

    return render_template('products/form.html', product=p, units=units, categories=cats, warehouses=warehouses, conversions=conversions)
        

@products_bp.route('/edit/')
@login_required
@require_permission('products', 'view')
def edit_missing_id():
    flash('Vui lòng chọn một hàng hóa cụ thể để chỉnh sửa.', 'warning')
    return redirect(url_for('products.index'))


@products_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('products', 'delete')
def delete(id):
    p = Product.query.get_or_404(id)
    from app.domains.inventory.models import StockInItem, StockOutItem
    has_txn = (db.session.query(StockInItem).filter_by(product_id=p.id).count() > 0
               or db.session.query(StockOutItem).filter_by(product_id=p.id).count() > 0)
    if has_txn:
        p.is_active = False
        db.session.commit()
        flash(f'HH {p.code} đã vô hiệu hóa (có giao dịch liên quan).', 'warning')
    else:
        db.session.delete(p)
        db.session.commit()
        flash(f'Xóa hàng hóa {p.code} thành công!', 'success')
    return redirect(url_for('products.index'))


@products_bp.route('/export/excel')
@login_required
@require_permission('products', 'export')
def export_excel():
    products = Product.query.order_by(Product.code).all()
    output = ExcelExporter.export_products(products)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True,
                     download_name=f'hang_hoa_{datetime.now().strftime("%Y%m%d")}.xlsx')


@products_bp.route('/import/excel', methods=['POST'])
@login_required
@require_permission('products', 'create')
def import_excel():
    if 'file' not in request.files:
        flash('Vui lòng chọn file Excel!', 'danger')
        return redirect(url_for('products.index'))
    file = request.files['file']
    if not file.filename.endswith(('.xlsx', '.xls')):
        flash('File không hợp lệ!', 'danger')
        return redirect(url_for('products.index'))
    imported, updated, errors = ExcelImporter.import_products(file)
    flash(f'Import thành công: {imported} mới, {updated} cập nhật.', 'success')
    for err in errors[:5]:
        flash(f'Lỗi: {err}', 'warning')
    return redirect(url_for('products.index'))


@products_bp.route('/template/excel')
@login_required
@require_permission('products', 'view')
def download_template():
    sample = pd.DataFrame([{
        'Mã hàng': 'HH001', 'Tên hàng': 'Sản phẩm mẫu',
        'Đơn vị': 'Cái', 'Nhóm hàng': 'Nhóm 1',
        'Giá mua': 100000, 'Giá bán': 150000,
        'Thuế VAT (%)': 10, 'Tồn tối thiểu': 10,
    }])
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        sample.to_excel(writer, index=False, sheet_name='Hàng hóa')
    output.seek(0)
    return send_file(output,
                     mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                     as_attachment=True, download_name='mau_import_hang_hoa.xlsx')
