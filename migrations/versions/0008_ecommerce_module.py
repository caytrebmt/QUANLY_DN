"""ensure ecommerce module

Replaces ``_ensure_ecommerce_module()``. Creates the 8 e-commerce tables
with their indexes and seeds the E-commerce sidebar root plus its two children.

Revision ID: 0008ecommerce
Revises: 0007quotations
"""
from alembic import op
import sqlalchemy as sa

revision = '0008ecommerce'
down_revision = '0007quotations'
branch_labels = None
depends_on = None


def upgrade():
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS customer_accounts (
            id SERIAL PRIMARY KEY,
            customer_id INTEGER NULL REFERENCES customers(id),
            email VARCHAR(120) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            name VARCHAR(200) NOT NULL,
            phone VARCHAR(50) NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_login TIMESTAMP NULL
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS product_listings (
            id SERIAL PRIMARY KEY,
            product_id INTEGER NOT NULL UNIQUE REFERENCES products(id),
            slug VARCHAR(220) UNIQUE NOT NULL,
            web_title VARCHAR(220) NULL,
            web_description TEXT NULL,
            web_price NUMERIC(18,2) NULL,
            compare_at_price NUMERIC(18,2) NULL,
            image_url VARCHAR(500) NULL,
            seo_title VARCHAR(220) NULL,
            seo_description VARCHAR(300) NULL,
            stock_cached NUMERIC(18,3) DEFAULT 0,
            stock_synced_at TIMESTAMP NULL,
            is_published BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS customer_sessions (
            id SERIAL PRIMARY KEY,
            session_key VARCHAR(120) UNIQUE NOT NULL,
            customer_id INTEGER NULL REFERENCES customers(id),
            name VARCHAR(200) NULL,
            email VARCHAR(120) NULL,
            phone VARCHAR(50) NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP NULL
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS cart (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES customer_sessions(id),
            customer_id INTEGER NULL REFERENCES customers(id),
            status VARCHAR(20) DEFAULT 'active',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS cart_items (
            id SERIAL PRIMARY KEY,
            cart_id INTEGER NOT NULL REFERENCES cart(id) ON DELETE CASCADE,
            listing_id INTEGER NOT NULL REFERENCES product_listings(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            quantity NUMERIC(18,3) NOT NULL DEFAULT 1,
            unit_price NUMERIC(18,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS promotions (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            name VARCHAR(200) NOT NULL,
            description TEXT NULL,
            discount_type VARCHAR(20) DEFAULT 'percent',
            discount_value NUMERIC(18,2) DEFAULT 0,
            min_order_amount NUMERIC(18,2) DEFAULT 0,
            starts_at TIMESTAMP NULL,
            ends_at TIMESTAMP NULL,
            is_active BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS reviews (
            id SERIAL PRIMARY KEY,
            listing_id INTEGER NOT NULL REFERENCES product_listings(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            customer_id INTEGER NULL REFERENCES customers(id),
            customer_name VARCHAR(200) NULL,
            rating INTEGER NOT NULL DEFAULT 5,
            title VARCHAR(200) NULL,
            content TEXT NULL,
            status VARCHAR(20) DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS online_orders (
            id SERIAL PRIMARY KEY,
            code VARCHAR(50) UNIQUE NOT NULL,
            session_id INTEGER NULL REFERENCES customer_sessions(id),
            customer_id INTEGER NULL REFERENCES customers(id),
            promotion_id INTEGER NULL REFERENCES promotions(id),
            customer_name VARCHAR(200) NOT NULL,
            customer_phone VARCHAR(50) NULL,
            customer_email VARCHAR(120) NULL,
            shipping_address VARCHAR(500) NULL,
            subtotal NUMERIC(18,2) DEFAULT 0,
            discount_amount NUMERIC(18,2) DEFAULT 0,
            shipping_fee NUMERIC(18,2) DEFAULT 0,
            vat_amount NUMERIC(18,2) DEFAULT 0,
            total_amount NUMERIC(18,2) DEFAULT 0,
            status VARCHAR(20) DEFAULT 'new',
            sync_status VARCHAR(20) DEFAULT 'pending',
            sync_error TEXT NULL,
            stock_out_id INTEGER NULL REFERENCES stock_outs(id),
            note TEXT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            synced_at TIMESTAMP NULL
        )
    """))
    op.execute(sa.text("""
        CREATE TABLE IF NOT EXISTS online_order_items (
            id SERIAL PRIMARY KEY,
            online_order_id INTEGER NOT NULL REFERENCES online_orders(id) ON DELETE CASCADE,
            listing_id INTEGER NULL REFERENCES product_listings(id),
            product_id INTEGER NOT NULL REFERENCES products(id),
            product_name_snapshot VARCHAR(250) NULL,
            quantity NUMERIC(18,3) NOT NULL,
            unit_price NUMERIC(18,2) NOT NULL,
            amount NUMERIC(18,2) DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """))
    for ddl in [
        "CREATE INDEX IF NOT EXISTS ix_product_listings_published ON product_listings(is_published)",
        "CREATE INDEX IF NOT EXISTS ix_online_orders_sync_status ON online_orders(sync_status)",
        "CREATE INDEX IF NOT EXISTS ix_online_orders_created_at ON online_orders(created_at)",
        "CREATE INDEX IF NOT EXISTS ix_cart_session_status ON cart(session_id, status)",
    ]:
        op.execute(sa.text(ddl))

    op.execute(sa.text("""
        INSERT INTO menus (code, name, parent_id, url, icon, order_no, module, roles, is_active)
        VALUES ('ECOMMERCE_ROOT', 'E-commerce', NULL, NULL, 'fas fa-store', 58, 'ecommerce', '', true)
        ON CONFLICT (code) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO menus (code, name, parent_id, url, icon, order_no, module, roles, is_active)
        VALUES (
            'ECOMMERCE_LISTINGS', 'Sản phẩm web',
            (SELECT id FROM menus WHERE code='ECOMMERCE_ROOT'),
            '/ecommerce/listings', 'fas fa-tags', 1, 'ecommerce', '', true
        )
        ON CONFLICT (code) DO NOTHING
    """))
    op.execute(sa.text("""
        INSERT INTO menus (code, name, parent_id, url, icon, order_no, module, roles, is_active)
        VALUES (
            'ECOMMERCE_ORDERS', 'Đơn online',
            (SELECT id FROM menus WHERE code='ECOMMERCE_ROOT'),
            '/ecommerce/orders', 'fas fa-receipt', 2, 'ecommerce', '', true
        )
        ON CONFLICT (code) DO NOTHING
    """))
    for code in ('ECOMMERCE_ROOT', 'ECOMMERCE_LISTINGS', 'ECOMMERCE_ORDERS'):
        for role in ('admin', 'accountant', 'warehouse'):
            op.execute(sa.text(
                "INSERT INTO menu_roles (menu_id, role) "
                "SELECT id, :role FROM menus WHERE code=:code "
                "ON CONFLICT DO NOTHING"
            ).bindparams(role=role, code=code))


def downgrade():
    op.execute(sa.text("DROP TABLE IF EXISTS online_order_items"))
    op.execute(sa.text("DROP TABLE IF EXISTS online_orders"))
    op.execute(sa.text("DROP TABLE IF EXISTS reviews"))
    op.execute(sa.text("DROP TABLE IF EXISTS promotions"))
    op.execute(sa.text("DROP TABLE IF EXISTS cart_items"))
    op.execute(sa.text("DROP TABLE IF EXISTS cart"))
    op.execute(sa.text("DROP TABLE IF EXISTS customer_sessions"))
    op.execute(sa.text("DROP TABLE IF EXISTS product_listings"))
    op.execute(sa.text("DROP TABLE IF EXISTS customer_accounts"))
    op.execute(sa.text("DELETE FROM menus WHERE code IN ('ECOMMERCE_ROOT','ECOMMERCE_LISTINGS','ECOMMERCE_ORDERS')"))
