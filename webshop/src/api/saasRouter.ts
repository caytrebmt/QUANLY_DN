import { Router, Request, Response } from 'express';
import { query, isDbConnected } from '../db/index';

export const saasRouter = Router();

// Helper to determine language code ('vi' or 'en')
const getLang = (req: Request): 'vi' | 'en' => {
  const lang = (req.query.lang || req.headers['accept-language'] || 'vi').toString().toLowerCase();
  return lang.startsWith('en') ? 'en' : 'vi';
};

// ==========================================
// 1. LANGUAGES & TRANSLATIONS DICTIONARY
// ==========================================
saasRouter.get('/languages', async (req, res) => {
  if (!isDbConnected()) {
    return res.json({
      ok: true,
      data: [
        { code: 'vi', name: 'Tiếng Việt', flag_icon: '🇻🇳', is_default: true, is_active: true },
        { code: 'en', name: 'English', flag_icon: '🇬🇧', is_default: false, is_active: true },
      ],
    });
  }

  try {
    const result = await query('SELECT * FROM sys_languages WHERE is_active = TRUE ORDER BY is_default DESC');
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

saasRouter.get('/translations/all', async (req: Request, res: Response) => {
  if (!isDbConnected()) {
    return res.json({ ok: true, data: [] });
  }

  try {
    const result = await query(
      `SELECT DISTINCT translation_key as key, category,
              MAX(CASE WHEN lang_code = 'vi' THEN translation_value END) as vi,
              MAX(CASE WHEN lang_code = 'en' THEN translation_value END) as en
       FROM sys_translations
       GROUP BY translation_key, category
       ORDER BY category ASC, translation_key ASC`
    );
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

saasRouter.post('/translations', async (req: Request, res: Response) => {
  const { key, category = 'common', vi, en } = req.body;
  if (!key) {
    return res.status(400).json({ ok: false, error: 'Key is required' });
  }

  if (!isDbConnected()) {
    return res.json({ ok: true, message: 'Saved locally in frontend state' });
  }

  try {
    if (vi !== undefined) {
      await query(
        `INSERT INTO sys_translations (lang_code, category, translation_key, translation_value)
         VALUES ('vi', $1, $2, $3)
         ON CONFLICT (lang_code, translation_key) DO UPDATE SET translation_value = $3, category = $1`,
        [category, key, vi]
      );
    }
    if (en !== undefined) {
      await query(
        `INSERT INTO sys_translations (lang_code, category, translation_key, translation_value)
         VALUES ('en', $1, $2, $3)
         ON CONFLICT (lang_code, translation_key) DO UPDATE SET translation_value = $3, category = $1`,
        [category, key, en]
      );
    }
    res.json({ ok: true, message: 'Translation saved successfully' });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

saasRouter.delete('/translations/:key', async (req: Request, res: Response) => {
  const { key } = req.params;
  if (!isDbConnected()) {
    return res.json({ ok: true, message: 'Deleted locally' });
  }

  try {
    await query('DELETE FROM sys_translations WHERE translation_key = $1', [key]);
    res.json({ ok: true, message: 'Translation key deleted' });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ==========================================
// 2. SYSTEM SETTINGS & CONFIGURATION
// ==========================================
saasRouter.get('/settings', async (req: Request, res: Response) => {
  const lang = getLang(req);
  if (!isDbConnected()) {
    return res.json({
      ok: true,
      data: [
        { setting_key: 'company_name', setting_value: lang === 'en' ? 'ERPACC VIETNAM CO., LTD' : 'CÔNG TY TNHH ERPACC VIỆT NAM' },
        { setting_key: 'company_tax_code', setting_value: '0102030405' },
        { setting_key: 'company_address', setting_value: lang === 'en' ? '8th Floor, Innovation Building, Hanoi' : 'Tầng 8, Tòa nhà Innovation, Hà Nội' },
        { setting_key: 'company_phone', setting_value: '0988 123 456' },
      ],
    });
  }

  try {
    const result = await query('SELECT * FROM sys_settings ORDER BY setting_key ASC');
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ==========================================
// 3. DYNAMIC MENUS (MULTILINGUAL)
// ==========================================
saasRouter.get('/menus', async (req: Request, res: Response) => {
  const lang = getLang(req);
  if (!isDbConnected()) {
    const mockMenus = [
      { id: 1, code: 'DASHBOARD', title: lang === 'en' ? 'Dashboard Overview' : 'Tổng quan (Dashboard)', path: '/saas/dashboard', icon: 'LayoutDashboard' },
      { id: 2, code: 'QUOTATIONS', title: lang === 'en' ? 'Customer Quotations' : 'Báo giá khách hàng', path: '/saas/quotations', icon: 'FileText' },
      { id: 3, code: 'SALES_ORDERS', title: lang === 'en' ? 'Sales Orders' : 'Đơn hàng bán', path: '/saas/orders', icon: 'ShoppingCart' },
      { id: 4, code: 'CUSTOMERS', title: lang === 'en' ? 'Customers' : 'Khách hàng', path: '/saas/customers', icon: 'Users' },
      { id: 5, code: 'SUPPLIERS', title: lang === 'en' ? 'Suppliers' : 'Nhà cung cấp', path: '/saas/suppliers', icon: 'Truck' },
      { id: 6, code: 'PRODUCTS', title: lang === 'en' ? 'Products & Items' : 'Sản phẩm & Hàng hóa', path: '/saas/products', icon: 'Package' },
      { id: 7, code: 'CATEGORIES_UOM', title: lang === 'en' ? 'Categories & UOM' : 'Danh mục & Đơn vị tính', path: '/saas/categories-units', icon: 'Tags' },
      { id: 8, code: 'INVENTORY', title: lang === 'en' ? 'Warehouse Inventory' : 'Quản lý kho hàng', path: '/saas/inventory', icon: 'Boxes' },
      { id: 9, code: 'FINANCE_INVOICE', title: lang === 'en' ? 'Invoices & Receipts' : 'Hóa đơn & Thu chi', path: '/saas/finance-invoices', icon: 'Receipt' },
      { id: 10, code: 'REPORTS', title: lang === 'en' ? 'Reports & Analytics' : 'Báo cáo & Phân tích', path: '/saas/reports', icon: 'BarChart3' },
      { id: 11, code: 'SETTINGS', title: lang === 'en' ? 'System Settings' : 'Cấu hình hệ thống', path: '/saas/settings', icon: 'Settings' },
    ];
    return res.json({ ok: true, data: mockMenus });
  }

  try {
    const result = await query(
      `SELECT id, code, path, icon, parent_id, sort_order, 
              CASE WHEN $1 = 'en' THEN title_en ELSE title_vi END as title 
       FROM sys_menus WHERE is_active = TRUE ORDER BY sort_order ASC`,
      [lang]
    );
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ==========================================
// 4. ROLES & PERMISSIONS (MULTILINGUAL)
// ==========================================
saasRouter.get('/roles', async (req: Request, res: Response) => {
  const lang = getLang(req);
  if (!isDbConnected()) {
    return res.json({
      ok: true,
      data: [
        { id: 1, code: 'ADMIN', name: lang === 'en' ? 'System Administrator' : 'Quản trị viên toàn hệ thống' },
        { id: 2, code: 'SALES', name: lang === 'en' ? 'Sales Representative' : 'Nhân viên Kinh doanh' },
        { id: 3, code: 'ACCOUNTANT', name: lang === 'en' ? 'Chief Accountant' : 'Kế toán viên' },
        { id: 4, code: 'WAREHOUSE', name: lang === 'en' ? 'Warehouse Manager' : 'Thủ kho' },
      ],
    });
  }

  try {
    const result = await query(
      `SELECT id, code, 
              CASE WHEN $1 = 'en' THEN name_en ELSE name_vi END as name,
              CASE WHEN $1 = 'en' THEN description_en ELSE description_vi END as description
       FROM sys_roles ORDER BY id ASC`,
      [lang]
    );
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ==========================================
// 5. PRODUCTS (MULTILINGUAL)
// ==========================================
saasRouter.get('/products', async (req: Request, res: Response) => {
  const lang = getLang(req);
  if (!isDbConnected()) {
    return res.json({ ok: true, message: 'Running with local mock products' });
  }

  try {
    const result = await query(
      `SELECT p.id, p.sku, p.cost_price, p.selling_price, p.web_price, p.stock_quantity, p.min_stock, p.image_url, p.is_published,
              CASE WHEN $1 = 'en' THEN p.name_en ELSE p.name_vi END as name,
              CASE WHEN $1 = 'en' THEN p.description_en ELSE p.description_vi END as description,
              CASE WHEN $1 = 'en' THEN c.name_en ELSE c.name_vi END as category_name,
              CASE WHEN $1 = 'en' THEN u.name_en ELSE u.name_vi END as uom_name
       FROM products p 
       LEFT JOIN categories c ON p.category_id = c.id 
       LEFT JOIN uom u ON p.uom_id = u.id 
       ORDER BY p.id DESC`,
      [lang]
    );
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

// ==========================================
// 6. CATEGORIES & UOM (MULTILINGUAL)
// ==========================================
saasRouter.get('/categories', async (req: Request, res: Response) => {
  const lang = getLang(req);
  if (!isDbConnected()) return res.json({ ok: true, data: [] });
  try {
    const result = await query(
      `SELECT id, code, parent_id, is_active,
              CASE WHEN $1 = 'en' THEN name_en ELSE name_vi END as name,
              CASE WHEN $1 = 'en' THEN description_en ELSE description_vi END as description
       FROM categories ORDER BY id ASC`,
      [lang]
    );
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

saasRouter.get('/uom', async (req: Request, res: Response) => {
  const lang = getLang(req);
  if (!isDbConnected()) return res.json({ ok: true, data: [] });
  try {
    const result = await query(
      `SELECT id, code, is_fractional,
              CASE WHEN $1 = 'en' THEN name_en ELSE name_vi END as name,
              CASE WHEN $1 = 'en' THEN description_en ELSE description_vi END as description
       FROM uom ORDER BY id ASC`,
      [lang]
    );
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

// Other endpoints
saasRouter.get('/customers', async (req, res) => {
  if (!isDbConnected()) return res.json({ ok: true, message: 'Running with mock customers' });
  try {
    const result = await query('SELECT * FROM customers ORDER BY id DESC');
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

saasRouter.get('/suppliers', async (req, res) => {
  if (!isDbConnected()) return res.json({ ok: true, message: 'Running with mock suppliers' });
  try {
    const result = await query('SELECT * FROM suppliers ORDER BY id DESC');
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

saasRouter.get('/quotations', async (req, res) => {
  if (!isDbConnected()) return res.json({ ok: true, message: 'Running with mock quotations' });
  try {
    const result = await query(
      `SELECT q.*, c.name as customer_name, c.phone as customer_phone 
       FROM quotations q 
       LEFT JOIN customers c ON q.customer_id = c.id 
       ORDER BY q.id DESC`
    );
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});

saasRouter.get('/orders', async (req, res) => {
  if (!isDbConnected()) return res.json({ ok: true, message: 'Running with mock orders' });
  try {
    const result = await query(
      `SELECT o.*, c.name as customer_name, c.phone as customer_phone 
       FROM sales_orders o 
       LEFT JOIN customers c ON o.customer_id = c.id 
       ORDER BY o.id DESC`
    );
    res.json({ ok: true, data: result.rows });
  } catch (error: any) {
    res.status(500).json({ ok: false, error: error.message });
  }
});
