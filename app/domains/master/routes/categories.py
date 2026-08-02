from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from app.database import db
from app.domains.master.models import Category
from app.shared.authz import require_permission
from app.domains.master.services.product_code_service import (
    generate_product_code,
    slug_code_from_name,
    generate_unique_code,
)

categories_bp = Blueprint('categories', __name__, url_prefix='/categories')


@categories_bp.route('/')
@login_required
@require_permission('products', 'view')
def index():
    from sqlalchemy import func
    from app.domains.master.models import Product
    cats = Category.query.order_by(Category.code).all()
    counts_raw = db.session.query(
        Product.category_id, func.count(Product.id)
    ).filter(Product.category_id.isnot(None)).group_by(Product.category_id).all()
    product_counts = {cid: cnt for cid, cnt in counts_raw}
    return render_template('categories/index.html', cats=cats, product_counts=product_counts)


@categories_bp.route('/create', methods=['GET', 'POST'])
@login_required
@require_permission('products', 'create')
def create():
    if request.method == 'POST':
        code = request.form.get('code', '').strip().upper()
        name = request.form.get('name', '').strip()
        if not name:
            flash('Mã và tên nhóm hàng không được để trống!', 'danger')
            return render_template('categories/form.html', cat=None,
                                   all_cats=Category.query.order_by(Category.code).all())
        code = generate_product_code(name=name, user_code=code)
        if Category.query.filter_by(code=code).first():
            flash(f'Mã nhóm {code} đã tồn tại!', 'danger')
            return render_template('categories/form.html', cat=None,
                                   all_cats=Category.query.order_by(Category.code).all())
        c = Category(
            code=code, name=name,
            parent_id=request.form.get('parent_id', type=int) or None,
            description=request.form.get('description', '').strip()
        )
        db.session.add(c)
        db.session.commit()
        flash(f'Thêm nhóm hàng {code} thành công!', 'success')
        return redirect(url_for('categories.index'))
    return render_template('categories/form.html', cat=None,
                           all_cats=Category.query.order_by(Category.code).all())


@categories_bp.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
@require_permission('products', 'edit')
def edit(id):
    c = Category.query.get_or_404(id)
    if request.method == 'POST':
        c.name = request.form.get('name', '').strip()
        c.parent_id = request.form.get('parent_id', type=int) or None
        c.description = request.form.get('description', '').strip()
        c.is_active = request.form.get('is_active') == 'on'
        db.session.commit()
        flash(f'Cập nhật nhóm {c.code} thành công!', 'success')
        return redirect(url_for('categories.index'))
    all_cats = Category.query.filter(Category.id != id).order_by(Category.code).all()
    return render_template('categories/form.html', cat=c, all_cats=all_cats)


@categories_bp.route('/delete/<int:id>', methods=['POST'])
@login_required
@require_permission('products', 'delete')
def delete(id):
    c = Category.query.get_or_404(id)
    c.is_active = False
    db.session.commit()
    flash(f'Đã vô hiệu hóa nhóm {c.code}.', 'warning')
    return redirect(url_for('categories.index'))
