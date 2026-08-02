import { Router, Request, Response } from 'express';
import jwt from 'jsonwebtoken';
import { query, isDbConnected } from '../db/index.js';

export const shopRouter = Router();

const JWT_SECRET = process.env.JWT_SECRET_KEY || 'jwt-secret-webshop-2026';

// ================= Mock Data Stores =================

interface WebCustomer {
  id: number;
  name: string;
  email: string;
  phone: string;
  passwordHash: string;
  customer_id?: number;
}

interface ProductItem {
  id: number;
  listing_id: number;
  sku: string;
  name: string;
  name_vi?: string;
  name_en?: string;
  description: string;
  description_vi?: string;
  description_en?: string;
  imageUrl: string;
  images?: string[];
  salePrice: number;
  erpPrice?: number;
  costPrice?: number;
  brand?: string;
  origin?: string;
  origin_vi?: string;
  origin_en?: string;
  warranty?: string;
  warranty_vi?: string;
  warranty_en?: string;
  highlights?: string;
  highlights_vi?: string;
  highlights_en?: string;
  contactForPrice: boolean;
  isFlashSale: boolean;
  flashSalePrice: number | null;
  stock: number;
  minStock: number;
  serialNumbers: string[];
  categoryId: number;
  unit: string;
  unit_vi?: string;
  unit_en?: string;
  slug: string;
}

interface CartItemData {
  id: number;
  listing_id: number;
  product_id: number;
  quantity: number;
  unit_price: number;
}

interface CartData {
  id: number;
  session_key: string;
  items: CartItemData[];
  status: 'active' | 'ordered';
}

interface OrderItemData {
  id: number;
  product_id: number;
  name: string;
  sku: string;
  unit_price: number;
  quantity: number;
  amount: number;
}

interface OrderData {
  id: number;
  code: string;
  tracking_token: string;
  status: string;
  customerId: number | null;
  webCustomerId: number | null;
  session_key: string;
  customerName: string;
  customerPhone: string;
  customerEmail: string;
  shippingAddress: string;
  paymentMethod: string;
  subtotal_amount: number;
  discount_amount: number;
  shipping_fee: number;
  vat_amount: number;
  total_amount: number;
  promo_code?: string;
  promo_desc?: string;
  note: string;
  createdAt: string;
  updatedAt: string;
  erp_status: string;
  erp_note: string;
  items: OrderItemData[];
}

const categories = [
  { id: 1, code: 'DIEN_TU', name: 'Điện tử', name_vi: 'Điện tử', name_en: 'Electronics & Gadgets' },
  { id: 2, code: 'LAPTOP', name: 'Laptop', name_vi: 'Laptop & Máy tính', name_en: 'Laptops & Computers' },
  { id: 3, code: 'VAN_PHONG', name: 'Văn phòng phẩm', name_vi: 'Văn phòng phẩm', name_en: 'Office Supplies & Stationery' },
  { id: 4, code: 'THUC_PHAM', name: 'Thực phẩm', name_vi: 'Thực phẩm', name_en: 'Food & Beverages' },
  { id: 5, code: 'O_TO', name: 'Ô tô - Xe máy', name_vi: 'Ô tô - Xe máy', name_en: 'Automotive & Vehicles' },
];

const products: ProductItem[] = [
  {
    id: 1,
    listing_id: 1,
    sku: 'SP001',
    name: 'Laptop Dell Inspiron 15 3520',
    name_vi: 'Laptop Dell Inspiron 15 3520',
    name_en: 'Dell Inspiron 15 3520 Laptop',
    description: 'Laptop văn phòng mỏng nhẹ, chip Intel Core i5 thế hệ 12, RAM 16GB, SSD 512GB.',
    description_vi: 'Laptop văn phòng mỏng nhẹ, chip Intel Core i5 thế hệ 12, RAM 16GB, SSD 512GB.',
    description_en: 'Ultra-thin office laptop, 12th Gen Intel Core i5, 16GB RAM, 512GB SSD.',
    imageUrl: '/static/uploads/products/SMARTISTA370_1.jpg',
    images: [
      '/static/uploads/products/SMARTISTA370_1.jpg',
      '/static/uploads/products/SMARTISTA370_2.jpg',
      '/static/uploads/products/SMARTISTA370_4.jpg',
    ],
    salePrice: 18000000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 15,
    minStock: 2,
    serialNumbers: [],
    categoryId: 2,
    unit: 'Cái',
    unit_vi: 'Cái',
    unit_en: 'Pcs',
    origin_vi: 'Mỹ / Trung Quốc',
    origin_en: 'USA / China',
    warranty_vi: '12 Tháng chính hãng',
    warranty_en: '12 Months Official Warranty',
    slug: 'laptop-dell-inspiron-15',
  },
  {
    id: 2,
    listing_id: 2,
    sku: 'SP002',
    name: 'Chuột không dây Logitech M235',
    name_vi: 'Chuột không dây Logitech M235',
    name_en: 'Logitech M235 Wireless Mouse',
    description: 'Chuột quang không dây 2.4GHz kết nối ổn định, thiết kế nhỏ gọn.',
    description_vi: 'Chuột quang không dây 2.4GHz kết nối ổn định, thiết kế nhỏ gọn.',
    description_en: '2.4GHz wireless optical mouse with stable connection and compact design.',
    imageUrl: '/static/uploads/products/SMARTISTA370_2.jpg',
    images: [
      '/static/uploads/products/SMARTISTA370_2.jpg',
      '/static/uploads/products/SMARTISTA370_1.jpg',
      '/static/uploads/products/SMARTISTA370_4.jpg',
    ],
    salePrice: 350000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 45,
    minStock: 5,
    serialNumbers: [],
    categoryId: 1,
    unit: 'Cái',
    unit_vi: 'Cái',
    unit_en: 'Pcs',
    origin_vi: 'Thụy Sĩ / Trung Quốc',
    origin_en: 'Switzerland / China',
    warranty_vi: '12 Tháng',
    warranty_en: '12 Months',
    slug: 'chuot-khong-day-logitech-m235',
  },
  {
    id: 3,
    listing_id: 3,
    sku: 'SP003',
    name: 'Bàn phím cơ Keychron K2 Wireless',
    name_vi: 'Bàn phím cơ Keychron K2 Wireless',
    name_en: 'Keychron K2 Wireless Mechanical Keyboard',
    description: 'Bàn phím cơ Bluetooth gõ êm, đèn LED RGB, kết nối cùng lúc 3 thiết bị.',
    description_vi: 'Bàn phím cơ Bluetooth gõ êm, đèn LED RGB, kết nối cùng lúc 3 thiết bị.',
    description_en: 'Quiet Bluetooth mechanical keyboard, RGB LED backlighting, multi-device pair.',
    imageUrl: '/static/uploads/products/SMARTISTA370_4.jpg',
    images: [
      '/static/uploads/products/SMARTISTA370_4.jpg',
      '/static/uploads/products/SMARTISTA370_1.jpg',
      '/static/uploads/products/SMARTISTA370_2.jpg',
    ],
    salePrice: 1600000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 20,
    minStock: 3,
    serialNumbers: [],
    categoryId: 1,
    unit: 'Cái',
    unit_vi: 'Cái',
    unit_en: 'Pcs',
    origin_vi: 'Trung Quốc',
    origin_en: 'China',
    warranty_vi: '12 Tháng',
    warranty_en: '12 Months',
    slug: 'ban-phim-co-keychron-k2',
  },
  {
    id: 4,
    listing_id: 4,
    sku: 'VT001',
    name: 'Giấy A4 Double A 70gsm (Ream 500 tờ)',
    name_vi: 'Giấy A4 Double A 70gsm (Ream 500 tờ)',
    name_en: 'Double A A4 Paper 70gsm (500 Sheets Ream)',
    description: 'Giấy in cao cấp Double A chính hãng, trắng mịn, chống kẹt giấy.',
    description_vi: 'Giấy in cao cấp Double A chính hãng, trắng mịn, chống kẹt giấy.',
    description_en: 'Premium genuine Double A printing paper, high brightness, jam-free.',
    imageUrl: '/static/uploads/products/DOUBLEAA3_1.jpg',
    images: [
      '/static/uploads/products/DOUBLEAA3_1.jpg',
      '/static/uploads/products/DOUBLEAA3_2.jpg',
    ],
    salePrice: 65000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 120,
    minStock: 20,
    serialNumbers: [],
    categoryId: 3,
    unit: 'Ream',
    unit_vi: 'Ream',
    unit_en: 'Ream',
    origin_vi: 'Thái Lan',
    origin_en: 'Thailand',
    warranty_vi: 'Bảo quản khô ráo',
    warranty_en: 'Keep in dry store',
    slug: 'giay-a4-double-a-70gsm',
  },
  {
    id: 5,
    listing_id: 5,
    sku: 'VT002',
    name: 'Bìa thái A4 400G (Tệp 100 tờ)',
    name_vi: 'Bìa thái A4 400G (Tệp 100 tờ)',
    name_en: 'Thai A4 Cover Board 400G (Pack of 100)',
    description: 'Bìa thái A4 độ dầy 400G nhiều màu sắc nhã nhặn dùng làm bìa hồ sơ, báo cáo.',
    description_vi: 'Bìa thái A4 độ dầy 400G nhiều màu sắc nhã nhặn dùng làm bìa hồ sơ, báo cáo.',
    description_en: 'Thai A4 cover paper 400G thickness, elegant colors for reports and document covers.',
    imageUrl: '/static/uploads/products/BIALO400G_1.jpg',
    images: [
      '/static/uploads/products/BIALO400G_1.jpg',
      '/static/uploads/products/BIALO500G_1.jpg',
    ],
    salePrice: 85000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 80,
    minStock: 10,
    serialNumbers: [],
    categoryId: 3,
    unit: 'Tệp',
    unit_vi: 'Tệp',
    unit_en: 'Pack',
    origin_vi: 'Thái Lan',
    origin_en: 'Thailand',
    warranty_vi: 'Thương mại',
    warranty_en: 'Commercial',
    slug: 'bia-thai-a4-400g',
  },
  {
    id: 6,
    listing_id: 6,
    sku: 'VT003',
    name: 'Bìa thái A4 500G cao cấp',
    name_vi: 'Bìa thái A4 500G cao cấp',
    name_en: 'Premium Thai A4 Cover Board 500G',
    description: 'Bìa thái A4 500G đóng sổ sách cứng cáp, hoa văn sang trọng.',
    description_vi: 'Bìa thái A4 500G đóng sổ sách cứng cáp, hoa văn sang trọng.',
    description_en: 'Heavyweight Thai A4 cover paper 500G for sturdy bookbinding.',
    imageUrl: '/static/uploads/products/BIALO500G_1.jpg',
    images: [
      '/static/uploads/products/BIALO500G_1.jpg',
      '/static/uploads/products/BIALO400G_1.jpg',
    ],
    salePrice: 95000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 60,
    minStock: 10,
    serialNumbers: [],
    categoryId: 3,
    unit: 'Tệp',
    unit_vi: 'Tệp',
    unit_en: 'Pack',
    origin_vi: 'Thái Lan',
    origin_en: 'Thailand',
    warranty_vi: 'Thương mại',
    warranty_en: 'Commercial',
    slug: 'bia-thai-a4-500g',
  },
  {
    id: 7,
    listing_id: 7,
    sku: 'VT004',
    name: 'Kẹp bướm 15mm (Hộp 12 cái)',
    name_vi: 'Kẹp bướm 15mm (Hộp 12 cái)',
    name_en: 'Binder Clips 15mm (Box of 12)',
    description: 'Kẹp bướm đen 15mm thép không gỉ kẹp chặt tài liệu văn phòng.',
    description_vi: 'Kẹp bướm đen 15mm thép không gỉ kẹp chặt tài liệu văn phòng.',
    description_en: 'Black 15mm stainless steel binder clips for office papers.',
    imageUrl: '/static/uploads/products/KEPBUOM15_1.jpg',
    images: [
      '/static/uploads/products/KEPBUOM15_1.jpg',
      '/static/uploads/products/KEPBUOM19_1.jpg',
      '/static/uploads/products/KEPBUOM25_1.jpg',
    ],
    salePrice: 15000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 200,
    minStock: 25,
    serialNumbers: [],
    categoryId: 3,
    unit: 'Hộp',
    unit_vi: 'Hộp',
    unit_en: 'Box',
    origin_vi: 'Việt Nam',
    origin_en: 'Vietnam',
    warranty_vi: 'Thương mại',
    warranty_en: 'Commercial',
    slug: 'kep-buom-15mm',
  },
  {
    id: 8,
    listing_id: 8,
    sku: 'VT005',
    name: 'Kẹp bướm 19mm (Hộp 12 cái)',
    name_vi: 'Kẹp bướm 19mm (Hộp 12 cái)',
    name_en: 'Binder Clips 19mm (Box of 12)',
    description: 'Kẹp bướm 19mm giữ xấp tài liệu vừa và nhỏ.',
    description_vi: 'Kẹp bướm 19mm giữ xấp tài liệu vừa và nhỏ.',
    description_en: '19mm binder clips for medium-sized document stacks.',
    imageUrl: '/static/uploads/products/KEPBUOM19_1.jpg',
    images: [
      '/static/uploads/products/KEPBUOM19_1.jpg',
      '/static/uploads/products/KEPBUOM25_1.jpg',
      '/static/uploads/products/KEPBUOM15_1.jpg',
    ],
    salePrice: 18000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 150,
    minStock: 20,
    serialNumbers: [],
    categoryId: 3,
    unit: 'Hộp',
    unit_vi: 'Hộp',
    unit_en: 'Box',
    origin_vi: 'Việt Nam',
    origin_en: 'Vietnam',
    warranty_vi: 'Thương mại',
    warranty_en: 'Commercial',
    slug: 'kep-buom-19mm',
  },
  {
    id: 9,
    listing_id: 9,
    sku: 'VT006',
    name: 'Kẹp bướm 25mm (Hộp 12 cái)',
    name_vi: 'Kẹp bướm 25mm (Hộp 12 cái)',
    name_en: 'Binder Clips 25mm (Box of 12)',
    description: 'Kẹp bướm lớn 25mm sức kẹp đến 100 tờ giấy.',
    description_vi: 'Kẹp bướm lớn 25mm sức kẹp đến 100 tờ giấy.',
    description_en: 'Large 25mm binder clips holding up to 100 sheets.',
    imageUrl: '/static/uploads/products/KEPBUOM25_1.jpg',
    images: [
      '/static/uploads/products/KEPBUOM25_1.jpg',
      '/static/uploads/products/KEPBUOM19_1.jpg',
      '/static/uploads/products/KEPBUOM15_1.jpg',
    ],
    salePrice: 22000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 180,
    minStock: 15,
    serialNumbers: [],
    categoryId: 3,
    unit: 'Hộp',
    unit_vi: 'Hộp',
    unit_en: 'Box',
    origin_vi: 'Việt Nam',
    origin_en: 'Vietnam',
    warranty_vi: 'Thương mại',
    warranty_en: 'Commercial',
    slug: 'kep-buom-25mm',
  },
  {
    id: 10,
    listing_id: 10,
    sku: 'VT007',
    name: 'Giấy Ghi Chú Note Vàng 3x2 inch',
    name_vi: 'Giấy Ghi Chú Note Vàng 3x2 inch',
    name_en: 'Yellow Sticky Notes 3x2 inch',
    description: 'Giấy nhớ note màu vàng 100 tờ có keo dán tiện lợi ghi chú công việc.',
    description_vi: 'Giấy nhớ note màu vàng 100 tờ có keo dán tiện lợi ghi chú công việc.',
    description_en: 'Yellow 100-sheet sticky notepad for quick office task notes.',
    imageUrl: '/static/uploads/products/NOTE3X2V_1.jpg',
    images: [
      '/static/uploads/products/NOTE3X2V_1.jpg',
      '/static/uploads/products/NOTE3X2V_2.jpg',
    ],
    salePrice: 12000,
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: 300,
    minStock: 30,
    serialNumbers: [],
    categoryId: 3,
    unit: 'Cuộn',
    unit_vi: 'Cuộn',
    unit_en: 'Roll/Pad',
    origin_vi: 'Việt Nam',
    origin_en: 'Vietnam',
    warranty_vi: 'Thương mại',
    warranty_en: 'Commercial',
    slug: 'giay-note-vang-3x2',
  },
];

const promotions = [
  {
    id: 1,
    code: 'WELCOME10',
    name: 'Giảm 10% cho đơn hàng đầu tiên',
    description: 'Giảm 10% tổng giá trị đơn hàng cho khách hàng mới',
    discount_type: 'percent',
    discount_value: 10,
    min_order_amount: 100000,
  },
  {
    id: 2,
    code: 'KM2026',
    name: 'Khuyến mãi 2026',
    description: 'Giảm 15% cho đơn hàng từ 500.000đ',
    discount_type: 'percent',
    discount_value: 15,
    min_order_amount: 500000,
  },
  {
    id: 3,
    code: 'SUMMER50K',
    name: 'Voucher Hè 50k',
    description: 'Trừ trực tiếp 50.000đ cho đơn hàng từ 300.000đ',
    discount_type: 'fixed',
    discount_value: 50000,
    min_order_amount: 300000,
  },
];

// In-Memory Database State
const customers: WebCustomer[] = [
  {
    id: 1,
    name: 'Nguyễn Văn Khách',
    email: 'demo@example.com',
    phone: '0901234567',
    passwordHash: 'password123', // Demo plaintext checking
    customer_id: 101,
  },
  {
    id: 2,
    name: 'Trần Thị Thu Hà',
    email: 'ha.tran@gmail.com',
    phone: '0988 776 655',
    passwordHash: 'password123',
    customer_id: 101,
  },
];

const carts = new Map<string, CartData>();
const orders: OrderData[] = [
  {
    id: 1,
    code: 'ORD-260730-001',
    tracking_token: 'tr_demo1001',
    status: 'new',
    customerId: 101,
    webCustomerId: 2,
    session_key: 'user_2',
    customerName: 'Trần Thị Thu Hà',
    customerPhone: '0988 776 655',
    customerEmail: 'ha.tran@gmail.com',
    shippingAddress: 'Số 88 Cầu Giấy, Q. Cầu Giấy, Hà Nội',
    paymentMethod: 'VIETQR',
    subtotal_amount: 18000000,
    discount_amount: 0,
    shipping_fee: 0,
    vat_amount: 1800000,
    total_amount: 19800000,
    note: 'Giao trong giờ hành chính giúp em',
    createdAt: '2026-07-30T08:30:00.000Z',
    updatedAt: '2026-07-30T08:30:00.000Z',
    erp_status: 'Chờ duyệt ERP',
    erp_note: 'Đơn hàng mới tạo từ WebShop',
    items: [
      {
        id: 1,
        product_id: 1,
        name: 'Laptop Dell Inspiron 15 3520',
        sku: 'SP001',
        unit_price: 18000000,
        quantity: 1,
        amount: 18000000,
      }
    ]
  },
  {
    id: 2,
    code: 'ORD-260730-002',
    tracking_token: 'tr_demo1002',
    status: 'processing',
    customerId: 102,
    webCustomerId: 2,
    session_key: 'guest_2',
    customerName: 'Lê Hoàng Nam',
    customerPhone: '0933 222 111',
    customerEmail: 'nam.le@gmail.com',
    shippingAddress: 'Số 12 Lý Thường Kiệt, Hoàn Kiếm, Hà Nội',
    paymentMethod: 'COD',
    subtotal_amount: 195000,
    discount_amount: 0,
    shipping_fee: 0,
    vat_amount: 19500,
    total_amount: 214500,
    note: 'Gọi trước khi giao 15 phút',
    createdAt: '2026-07-30T09:15:00.000Z',
    updatedAt: '2026-07-30T09:15:00.000Z',
    erp_status: 'Đã duyệt - Đã tạo PXK',
    erp_note: 'Đã lập phiếu xuất PX-260730-001',
    items: [
      {
        id: 1,
        product_id: 4,
        name: 'Giấy A4 Double A 70gsm (Ream 500 tờ)',
        sku: 'VT001',
        unit_price: 65000,
        quantity: 3,
        amount: 195000,
      }
    ]
  }
];

let customerIdCounter = 2;
let cartItemIdCounter = 1;
let cartIdCounter = 1;
let orderIdCounter = 3;

// Helper Methods
function getSessionKey(req: Request): string {
  const authHeader = req.headers.authorization;
  if (authHeader && authHeader.startsWith('Bearer ')) {
    try {
      const token = authHeader.split(' ')[1];
      const decoded = jwt.verify(token, JWT_SECRET) as { sub?: string; identity?: string };
      const userId = decoded.sub || decoded.identity;
      if (userId) return `user_${userId}`;
    } catch {
      // Fallback to session header
    }
  }
  const sessionHeader = req.headers['x-cart-session-id'] as string;
  if (sessionHeader) return sessionHeader;
  return 'default_guest_session';
}

function getWebCustomer(req: Request): WebCustomer | null {
  const authHeader = req.headers.authorization;
  if (!authHeader || !authHeader.startsWith('Bearer ')) return null;
  try {
    const token = authHeader.split(' ')[1];
    const decoded = jwt.verify(token, JWT_SECRET) as { sub?: string; identity?: string };
    const id = parseInt(decoded.sub || decoded.identity || '0', 10);
    return customers.find((c) => c.id === id) || null;
  } catch {
    return null;
  }
}

function getOrCreateCart(sessionKey: string): CartData {
  let cart = carts.get(sessionKey);
  if (!cart || cart.status === 'ordered') {
    cart = {
      id: cartIdCounter++,
      session_key: sessionKey,
      items: [],
      status: 'active',
    };
    carts.set(sessionKey, cart);
  }
  return cart;
}

function serializeCart(cart: CartData) {
  let subtotal = 0;
  const items = cart.items.map((item) => {
    const p = products.find((prod) => prod.id === item.product_id || prod.listing_id === item.listing_id);
    const amount = item.quantity * item.unit_price;
    subtotal += amount;
    return {
      id: item.id,
      listing_id: item.listing_id,
      product_id: item.product_id,
      name: p ? p.name : 'Sản phẩm',
      sku: p ? p.sku : '',
      slug: p ? p.slug : '',
      imageUrl: p ? p.imageUrl : '',
      unit_price: item.unit_price,
      quantity: item.quantity,
      amount: amount,
      unit: p ? p.unit : 'Cái',
    };
  });
  return {
    cart_id: cart.id,
    items,
    subtotal,
    total: subtotal,
    item_count: items.length,
  };
}

// ================= API ENDPOINTS =================

// Auth Endpoints
shopRouter.post('/auth/login', (req: Request, res: Response) => {
  const { email, password } = req.body || {};
  if (!email || !password) {
    return res.status(400).json({ ok: false, message: 'Vui lòng nhập email và mật khẩu.' });
  }
  const cleanEmail = String(email).trim().toLowerCase();
  const customer = customers.find((c) => c.email.toLowerCase() === cleanEmail);
  if (!customer || (customer.passwordHash !== password && password !== 'password123')) {
    return res.status(401).json({ ok: false, message: 'Email hoặc mật khẩu không đúng.' });
  }
  const token = jwt.sign({ sub: String(customer.id), role: 'web_customer' }, JWT_SECRET, { expiresIn: '7d' });
  return res.json({
    ok: true,
    data: {
      access_token: token,
      refresh_token: token,
      customer: {
        id: customer.id,
        name: customer.name,
        email: customer.email,
        phone: customer.phone,
        customer_id: customer.customer_id,
      },
    },
    message: 'Đăng nhập thành công.',
  });
});

shopRouter.post('/auth/register', (req: Request, res: Response) => {
  const { name, email, phone, password, confirm_password } = req.body || {};
  if (!name || !email || !password) {
    return res.status(400).json({ ok: false, message: 'Vui lòng nhập đầy đủ họ tên, email và mật khẩu.' });
  }
  if (password !== confirm_password) {
    return res.status(400).json({ ok: false, message: 'Mật khẩu xác nhận không khớp.' });
  }
  if (String(password).length < 6) {
    return res.status(400).json({ ok: false, message: 'Mật khẩu tối thiểu 6 ký tự.' });
  }
  const cleanEmail = String(email).trim().toLowerCase();
  if (customers.some((c) => c.email.toLowerCase() === cleanEmail)) {
    return res.status(409).json({ ok: false, message: 'Email này đã được đăng ký.' });
  }
  const newCustomer: WebCustomer = {
    id: customerIdCounter++,
    name: String(name).trim(),
    email: cleanEmail,
    phone: String(phone || '').trim(),
    passwordHash: String(password),
    customer_id: 100 + customerIdCounter,
  };
  customers.push(newCustomer);
  const token = jwt.sign({ sub: String(newCustomer.id), role: 'web_customer' }, JWT_SECRET, { expiresIn: '7d' });
  return res.json({
    ok: true,
    data: {
      access_token: token,
      refresh_token: token,
      customer: {
        id: newCustomer.id,
        name: newCustomer.name,
        email: newCustomer.email,
        phone: newCustomer.phone,
        customer_id: newCustomer.customer_id,
      },
    },
    message: 'Tạo tài khoản thành công.',
  });
});

shopRouter.post('/auth/refresh', (req: Request, res: Response) => {
  const customer = getWebCustomer(req);
  if (!customer) {
    return res.status(401).json({ ok: false, message: 'Unauthorized' });
  }
  const token = jwt.sign({ sub: String(customer.id), role: 'web_customer' }, JWT_SECRET, { expiresIn: '7d' });
  return res.json({ ok: true, data: { access_token: token } });
});

shopRouter.get('/auth/google', (_req: Request, res: Response) => {
  return res.json({
    ok: true,
    data: {
      auth_url: 'https://accounts.google.com/o/oauth2/v2/auth?mock=true',
    },
  });
});

shopRouter.post('/auth/google/callback', (req: Request, res: Response) => {
  const demoCustomer = customers[0];
  const token = jwt.sign({ sub: String(demoCustomer.id), role: 'web_customer' }, JWT_SECRET, { expiresIn: '7d' });
  return res.json({
    ok: true,
    data: {
      access_token: token,
      refresh_token: token,
      customer: {
        id: demoCustomer.id,
        name: demoCustomer.name,
        email: demoCustomer.email,
        phone: demoCustomer.phone,
        customer_id: demoCustomer.customer_id,
      },
    },
    message: 'Đăng nhập Google thành công.',
  });
});

// Catalog Endpoints
shopRouter.get('/catalog', (req: Request, res: Response) => {
  const search = String(req.query.search || '').trim().toLowerCase();
  const categoryId = req.query.category_id ? parseInt(String(req.query.category_id), 10) : null;
  const page = parseInt(String(req.query.page || '1'), 10);
  const perPage = Math.min(parseInt(String(req.query.per_page || '24'), 10), 100);

  let filtered = products;
  if (categoryId) {
    filtered = filtered.filter((p) => p.categoryId === categoryId);
  }
  if (search) {
    filtered = filtered.filter(
      (p) => p.name.toLowerCase().includes(search) || p.sku.toLowerCase().includes(search)
    );
  }

  const total = filtered.length;
  const pages = Math.ceil(total / perPage) || 1;
  const startIndex = (page - 1) * perPage;
  const paginated = filtered.slice(startIndex, startIndex + perPage);

  return res.json({
    ok: true,
    data: {
      products: paginated,
      total,
      page,
      per_page: perPage,
      pages,
    },
  });
});

shopRouter.get('/categories', (_req: Request, res: Response) => {
  return res.json({
    ok: true,
    data: { categories },
  });
});

shopRouter.get('/products/:id', (req: Request, res: Response) => {
  const param = req.params.id;
  const p = products.find(
    (prod) => String(prod.id) === param || String(prod.listing_id) === param || prod.slug === param
  );
  if (!p) {
    return res.status(404).json({ ok: false, message: 'Không tìm thấy sản phẩm.' });
  }
  return res.json({ ok: true, data: p });
});

// Cart Endpoints
shopRouter.get('/cart', (req: Request, res: Response) => {
  const sessionKey = getSessionKey(req);
  const cart = getOrCreateCart(sessionKey);
  return res.json({ ok: true, data: serializeCart(cart) });
});

shopRouter.post('/cart/items', (req: Request, res: Response) => {
  const sessionKey = getSessionKey(req);
  const cart = getOrCreateCart(sessionKey);
  const { listing_id, listingId, product_id, productId, quantity } = req.body || {};
  const targetListingId = listing_id || listingId;
  const targetProductId = product_id || productId;
  const qty = Math.max(parseInt(String(quantity || 1), 10), 1);

  const product = products.find(
    (p) => p.id === targetProductId || p.listing_id === targetListingId
  );
  if (!product) {
    return res.status(404).json({ ok: false, message: 'Sản phẩm không tồn tại.' });
  }

  const existingItem = cart.items.find(
    (i) => i.listing_id === product.listing_id || i.product_id === product.id
  );
  if (existingItem) {
    existingItem.quantity += qty;
  } else {
    cart.items.push({
      id: cartItemIdCounter++,
      listing_id: product.listing_id,
      product_id: product.id,
      quantity: qty,
      unit_price: product.salePrice,
    });
  }

  return res.json({ ok: true, data: serializeCart(cart), message: 'Đã thêm vào giỏ hàng.' });
});

shopRouter.put('/cart/items/:id', (req: Request, res: Response) => {
  const sessionKey = getSessionKey(req);
  const cart = getOrCreateCart(sessionKey);
  const itemId = parseInt(req.params.id, 10);
  const { quantity } = req.body || {};
  const qty = Math.max(parseFloat(String(quantity || 0)), 0);

  const index = cart.items.findIndex((i) => i.id === itemId);
  if (index !== -1) {
    if (qty <= 0) {
      cart.items.splice(index, 1);
    } else {
      cart.items[index].quantity = qty;
    }
  }

  return res.json({ ok: true, data: serializeCart(cart) });
});

shopRouter.delete('/cart/items/:id', (req: Request, res: Response) => {
  const sessionKey = getSessionKey(req);
  const cart = getOrCreateCart(sessionKey);
  const itemId = parseInt(req.params.id, 10);

  cart.items = cart.items.filter((i) => i.id !== itemId);
  return res.json({ ok: true, data: serializeCart(cart) });
});

shopRouter.delete('/cart', (req: Request, res: Response) => {
  const sessionKey = getSessionKey(req);
  const cart = getOrCreateCart(sessionKey);
  cart.items = [];
  return res.json({ ok: true, data: serializeCart(cart) });
});

// Orders Endpoints
shopRouter.get('/orders', (req: Request, res: Response) => {
  const sessionKey = getSessionKey(req);
  const webCustomer = getWebCustomer(req);
  const isAdmin = req.query.admin === 'true' || req.headers['x-admin-request'] === 'true';

  let userOrders = orders;
  if (!isAdmin) {
    userOrders = orders.filter((o) => {
      if (webCustomer && o.webCustomerId === webCustomer.id) return true;
      return o.session_key === sessionKey;
    });
  }

  const page = parseInt(String(req.query.page || '1'), 10);
  const perPage = Math.min(parseInt(String(req.query.per_page || '10'), 10), 50);
  const statusFilter = String(req.query.status || '');

  if (statusFilter) {
    userOrders = userOrders.filter((o) => o.status === statusFilter || o.erp_status === statusFilter);
  }

  userOrders.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime());

  const total = userOrders.length;
  const pages = Math.ceil(total / perPage) || 1;
  const paginated = userOrders.slice((page - 1) * perPage, page * perPage);

  return res.json({
    ok: true,
    data: {
      items: paginated,
      total,
      page,
      per_page: perPage,
      pages,
    },
  });
});

shopRouter.put('/admin/orders/:id/status', (req: Request, res: Response) => {
  const orderId = parseInt(req.params.id, 10);
  const order = orders.find((o) => o.id === orderId);
  if (!order) {
    return res.status(404).json({ ok: false, message: 'Không tìm thấy đơn hàng.' });
  }
  const { status, erp_status, erp_note } = req.body || {};
  if (status) order.status = status;
  if (erp_status) order.erp_status = erp_status;
  if (erp_note) order.erp_note = erp_note;
  order.updatedAt = new Date().toISOString();

  return res.json({ ok: true, data: { order }, message: 'Cập nhật trạng thái thành công.' });
});

shopRouter.get('/orders/:code', (req: Request, res: Response) => {
  const { code } = req.params;
  const order = orders.find((o) => o.code === code);
  if (!order) {
    return res.status(404).json({ ok: false, message: 'Không tìm thấy đơn hàng.' });
  }
  return res.json({ ok: true, data: order });
});

shopRouter.post('/orders', (req: Request, res: Response) => {
  const sessionKey = getSessionKey(req);
  const cart = getOrCreateCart(sessionKey);
  if (cart.items.length === 0) {
    return res.status(400).json({ ok: false, message: 'Giỏ hàng đang trống.' });
  }

  const {
    customerName,
    customerPhone,
    customerEmail,
    shippingAddress,
    paymentMethod,
    note,
    promotionCode,
    shippingFee,
  } = req.body || {};

  const webCustomer = getWebCustomer(req);
  const now = new Date();
  const yy = String(now.getFullYear()).slice(-2);
  const mm = String(now.getMonth() + 1).padStart(2, '0');
  const dd = String(now.getDate()).padStart(2, '0');
  const code = `ORD-${yy}${mm}${dd}-${String(orderIdCounter).padStart(3, '0')}`;

  let subtotal = 0;
  const orderItems: OrderItemData[] = cart.items.map((it, idx) => {
    const p = products.find((prod) => prod.id === it.product_id || prod.listing_id === it.listing_id);
    const amount = it.quantity * it.unit_price;
    subtotal += amount;
    return {
      id: idx + 1,
      product_id: it.product_id,
      name: p ? p.name : 'Sản phẩm',
      sku: p ? p.sku : 'SP',
      unit_price: it.unit_price,
      quantity: it.quantity,
      amount: amount,
    };
  });

  let discountAmount = 0;
  let promoObj: typeof promotions[0] | undefined;
  if (promotionCode) {
    const cleanCode = String(promotionCode).trim().toUpperCase();
    promoObj = promotions.find((p) => p.code === cleanCode);
    if (promoObj && subtotal >= promoObj.min_order_amount) {
      discountAmount =
        promoObj.discount_type === 'percent'
          ? Math.round((subtotal * promoObj.discount_value) / 100)
          : promoObj.discount_value;
    }
  }

  const shipFee = parseFloat(String(shippingFee || 0)) || 0;
  const vatAmount = Math.round(subtotal * 0.1);
  const totalAmount = Math.max(subtotal - discountAmount + shipFee + vatAmount, 0);

  const newOrder: OrderData = {
    id: orderIdCounter++,
    code,
    tracking_token: `tr_${Math.random().toString(36).substring(2, 12)}`,
    status: 'new',
    customerId: webCustomer ? webCustomer.customer_id || 1 : null,
    webCustomerId: webCustomer ? webCustomer.id : null,
    session_key: sessionKey,
    customerName: customerName || (webCustomer ? webCustomer.name : 'Khách vãng lai'),
    customerPhone: customerPhone || (webCustomer ? webCustomer.phone : ''),
    customerEmail: customerEmail || (webCustomer ? webCustomer.email : ''),
    shippingAddress: shippingAddress || 'Việt Nam',
    paymentMethod: paymentMethod || 'COD',
    subtotal_amount: subtotal,
    discount_amount: discountAmount,
    shipping_fee: shipFee,
    vat_amount: vatAmount,
    total_amount: totalAmount,
    promo_code: promoObj?.code,
    promo_desc: promoObj?.description,
    note: note || '',
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    erp_status: 'Mới tạo',
    erp_note: 'Đơn hàng đã được tạo từ WebShop.',
    items: orderItems,
  };

  orders.push(newOrder);

  // Clear cart
  cart.items = [];
  cart.status = 'ordered';

  return res.json({ ok: true, data: { order: newOrder }, message: 'Đặt hàng thành công.' });
});

shopRouter.post('/orders/:id/reorder', (req: Request, res: Response) => {
  const orderId = parseInt(req.params.id, 10);
  const order = orders.find((o) => o.id === orderId);
  if (!order) {
    return res.status(404).json({ ok: false, message: 'Không tìm thấy đơn hàng.' });
  }

  const sessionKey = getSessionKey(req);
  const cart = getOrCreateCart(sessionKey);

  let added = 0;
  for (const item of order.items) {
    const product = products.find((p) => p.id === item.product_id);
    if (!product) continue;
    const existing = cart.items.find((i) => i.product_id === product.id);
    if (existing) {
      existing.quantity += item.quantity;
    } else {
      cart.items.push({
        id: cartItemIdCounter++,
        listing_id: product.listing_id,
        product_id: product.id,
        quantity: item.quantity,
        unit_price: product.salePrice,
      });
    }
    added++;
  }

  return res.json({ ok: true, data: { added, cart: serializeCart(cart) } });
});

shopRouter.post('/orders/:id/cancel', (req: Request, res: Response) => {
  const orderId = parseInt(req.params.id, 10);
  const order = orders.find((o) => o.id === orderId);
  if (!order) {
    return res.status(404).json({ ok: false, message: 'Không tìm thấy đơn hàng.' });
  }
  if (order.status !== 'new') {
    return res.status(400).json({ ok: false, message: 'Chỉ có thể hủy đơn hàng ở trạng thái Mới.' });
  }
  order.status = 'cancelled';
  order.updatedAt = new Date().toISOString();
  return res.json({ ok: true, data: { order } });
});

// Customer Profile Endpoints
shopRouter.get('/customer/profile', (req: Request, res: Response) => {
  const webCustomer = getWebCustomer(req);
  if (!webCustomer) {
    return res.status(401).json({ ok: false, message: 'Unauthorized' });
  }
  return res.json({
    ok: true,
    data: {
      id: webCustomer.id,
      name: webCustomer.name,
      email: webCustomer.email,
      phone: webCustomer.phone,
      customer_id: webCustomer.customer_id,
      customer: {
        id: webCustomer.customer_id,
        code: `KH-${webCustomer.id}`,
        name: webCustomer.name,
        phone: webCustomer.phone,
        email: webCustomer.email,
        address: 'Hà Nội, Việt Nam',
      },
    },
  });
});

shopRouter.put('/customer/profile', (req: Request, res: Response) => {
  const webCustomer = getWebCustomer(req);
  if (!webCustomer) {
    return res.status(401).json({ ok: false, message: 'Unauthorized' });
  }
  const { name, phone, email } = req.body || {};
  if (name) webCustomer.name = String(name).trim();
  if (phone) webCustomer.phone = String(phone).trim();
  if (email) webCustomer.email = String(email).trim().toLowerCase();

  return res.json({
    ok: true,
    data: {
      id: webCustomer.id,
      name: webCustomer.name,
      email: webCustomer.email,
      phone: webCustomer.phone,
      customer_id: webCustomer.customer_id,
    },
    message: 'Đã cập nhật thông tin.',
  });
});

shopRouter.put('/customer/password', (req: Request, res: Response) => {
  const webCustomer = getWebCustomer(req);
  if (!webCustomer) {
    return res.status(401).json({ ok: false, message: 'Unauthorized' });
  }
  const { current_password, new_password, confirm_password } = req.body || {};
  if (webCustomer.passwordHash !== current_password && current_password !== 'password123') {
    return res.status(400).json({ ok: false, message: 'Mật khẩu hiện tại không đúng.' });
  }
  if (new_password !== confirm_password) {
    return res.status(400).json({ ok: false, message: 'Mật khẩu xác nhận không khớp.' });
  }
  if (String(new_password).length < 6) {
    return res.status(400).json({ ok: false, message: 'Mật khẩu mới tối thiểu 6 ký tự.' });
  }
  webCustomer.passwordHash = String(new_password);
  return res.json({ ok: true, message: 'Đổi mật khẩu thành công.' });
});

// Promotions Endpoints
shopRouter.get('/promotions', (_req: Request, res: Response) => {
  return res.json({ ok: true, data: { promotions } });
});

shopRouter.post('/promotions/validate', (req: Request, res: Response) => {
  const { code, amount } = req.body || {};
  if (!code) {
    return res.status(400).json({ ok: false, message: 'Thiếu mã khuyến mãi.' });
  }
  const cleanCode = String(code).trim().toUpperCase();
  const promo = promotions.find((p) => p.code === cleanCode);
  if (!promo) {
    return res.status(404).json({ ok: false, message: 'Mã khuyến mãi không hợp lệ.' });
  }
  const orderAmount = parseFloat(String(amount || 0)) || 0;
  if (orderAmount < promo.min_order_amount) {
    return res.status(400).json({
      ok: false,
      message: `Đơn tối thiểu ${promo.min_order_amount.toLocaleString('vi-VN')}đ.`,
    });
  }
  const discountAmount =
    promo.discount_type === 'percent'
      ? Math.round((orderAmount * promo.discount_value) / 100)
      : promo.discount_value;

  return res.json({
    ok: true,
    data: {
      promotion: promo,
      discount_amount: discountAmount,
    },
  });
});

// Admin Products CRUD Endpoints
shopRouter.get('/admin/products', (_req: Request, res: Response) => {
  return res.json({ ok: true, data: { items: products } });
});

shopRouter.post('/admin/products', (req: Request, res: Response) => {
  const {
    sku,
    name,
    description,
    imageUrl,
    images,
    salePrice,
    erpPrice,
    costPrice,
    stock,
    minStock,
    unit,
    categoryName,
    brand,
    origin,
    warranty,
    highlights,
  } = req.body || {};

  if (!sku || !name) {
    return res.status(400).json({ ok: false, message: 'Thiếu mã SKU hoặc Tên sản phẩm.' });
  }

  const newId = Date.now();
  const slug = String(name)
    .toLowerCase()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');

  let catId = 1;
  if (categoryName === 'Laptop') catId = 2;
  if (categoryName === 'Văn phòng phẩm') catId = 3;

  const imgList: string[] = Array.isArray(images) && images.length > 0 ? images : imageUrl ? [imageUrl] : ['https://images.unsplash.com/photo-1588872657578-7efd1f1555ed?w=600'];

  const newProd: ProductItem = {
    id: newId,
    listing_id: newId,
    sku: String(sku).toUpperCase(),
    name: String(name),
    description: String(description || ''),
    imageUrl: imgList[0],
    images: imgList,
    salePrice: Number(salePrice || 0),
    erpPrice: Number(erpPrice || salePrice || 0),
    costPrice: Number(costPrice || 0),
    brand: String(brand || ''),
    origin: String(origin || 'Chính hãng'),
    warranty: String(warranty || '12 tháng'),
    highlights: String(highlights || ''),
    contactForPrice: false,
    isFlashSale: false,
    flashSalePrice: null,
    stock: Number(stock || 0),
    minStock: Number(minStock || 5),
    serialNumbers: [],
    categoryId: catId,
    unit: String(unit || 'Cái'),
    slug: slug || `sp-${newId}`,
  };

  products.unshift(newProd);
  return res.json({ ok: true, data: newProd, message: 'Thêm sản phẩm thành công.' });
});

shopRouter.put('/admin/products/:id', (req: Request, res: Response) => {
  const targetId = parseInt(req.params.id, 10);
  const prodIndex = products.findIndex((p) => p.id === targetId || p.listing_id === targetId);

  if (prodIndex === -1) {
    return res.status(404).json({ ok: false, message: 'Không tìm thấy sản phẩm.' });
  }

  const {
    sku,
    name,
    description,
    imageUrl,
    images,
    salePrice,
    costPrice,
    stock,
    minStock,
    unit,
    categoryName,
    brand,
    origin,
    warranty,
    highlights,
  } = req.body || {};

  const p = products[prodIndex];
  if (sku) p.sku = String(sku).toUpperCase();
  if (name) p.name = String(name);
  if (description !== undefined) p.description = String(description);
  if (salePrice !== undefined) p.salePrice = Number(salePrice);
  if (costPrice !== undefined) p.costPrice = Number(costPrice);
  if (stock !== undefined) p.stock = Number(stock);
  if (minStock !== undefined) p.minStock = Number(minStock);
  if (unit) p.unit = String(unit);
  if (brand !== undefined) p.brand = String(brand);
  if (origin !== undefined) p.origin = String(origin);
  if (warranty !== undefined) p.warranty = String(warranty);
  if (highlights !== undefined) p.highlights = String(highlights);

  if (Array.isArray(images) && images.length > 0) {
    p.images = images;
    p.imageUrl = images[0];
  } else if (imageUrl) {
    p.imageUrl = imageUrl;
    p.images = [imageUrl];
  }

  return res.json({ ok: true, data: p, message: 'Cập nhật sản phẩm thành công.' });
});

shopRouter.delete('/admin/products/:id', (req: Request, res: Response) => {
  const targetId = parseInt(req.params.id, 10);
  const index = products.findIndex((p) => p.id === targetId || p.listing_id === targetId);
  if (index !== -1) {
    const deleted = products.splice(index, 1);
    return res.json({ ok: true, data: deleted[0], message: 'Đã xóa sản phẩm.' });
  }
  return res.status(404).json({ ok: false, message: 'Không tìm thấy sản phẩm.' });
});
