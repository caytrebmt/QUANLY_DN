import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  Package,
  Users,
  Truck,
  ArrowDownLeft,
  ArrowUpRight,
  FileSpreadsheet,
  Boxes,
  Receipt,
  Calculator,
  Settings,
  ShoppingBag,
  Building2,
  ChevronRight,
  LogOut,
  Warehouse,
  Tag,
  BarChart3,
  ClipboardList,
  Percent,
  ChevronLeft,
} from 'lucide-react';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';

interface SaaSSidebarProps {
  isOpen: boolean;
  onClose?: () => void;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

export const SaaSSidebar: React.FC<SaaSSidebarProps> = ({
  isOpen,
  onClose,
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const { user, logout } = useAuth();
  const { language, t } = useLanguage();

  const isEn = language === 'en';

  const navGroups = [
    {
      title: isEn ? 'OVERVIEW & SALES' : 'TỔNG QUAN & BÁN HÀNG',
      items: [
        { name: isEn ? 'Dashboard Overview' : 'Dashboard Overview', path: '/saas/dashboard', icon: LayoutDashboard },
        { name: isEn ? 'WebShop Orders' : 'Đơn Hàng WebShop', path: '/saas/web-orders', icon: ShoppingBag },
        { name: isEn ? 'Products & Materials' : 'Hàng hóa & Vật tư', path: '/saas/products', icon: Package },
        { name: isEn ? 'Categories & Units' : 'Danh mục & ĐVT', path: '/saas/categories-units', icon: Tag },
        { name: isEn ? 'Customers' : 'Khách hàng', path: '/saas/customers', icon: Users },
        { name: isEn ? 'Suppliers' : 'Nhà cung cấp', path: '/saas/suppliers', icon: Truck },
      ],
    },
    {
      title: isEn ? 'WAREHOUSE & DOCUMENTS' : 'QUẢN LÝ KHO & CHỨNG TỪ',
      items: [
        { name: isEn ? 'Warehouse Locations' : 'Địa điểm Kho bãi', path: '/saas/warehouses', icon: Warehouse },
        { name: isEn ? 'Stock In Receipt' : 'Nhập kho (Stock In)', path: '/saas/stock-in', icon: ArrowDownLeft },
        { name: isEn ? 'Stock Out Issue' : 'Xuất kho (Stock Out)', path: '/saas/stock-out', icon: ArrowUpRight },
        { name: isEn ? 'Stocktaking & Discrepancies' : 'Kiểm kê Kho & Lệch kho', path: '/saas/stocktaking', icon: ClipboardList },
        { name: isEn ? 'Commercial Quotations' : 'Báo giá Commercial', path: '/saas/quotations', icon: FileSpreadsheet },
        { name: isEn ? 'Stock Balance Report' : 'Báo cáo Tồn kho', path: '/saas/inventory', icon: Boxes },
      ],
    },
    {
      title: isEn ? 'FINANCE & ACCOUNTING' : 'TÀI CHÍNH & KẾ TOÁN',
      items: [
        { name: isEn ? 'Debts & Cash Flow' : 'Sổ Công nợ & Thu Chi', path: '/saas/debt', icon: Receipt },
        { name: isEn ? 'VAT Tax Filings' : 'Kê Khai Thuế GTGT (VAT)', path: '/saas/vat', icon: Percent },
        { name: isEn ? 'Accounting Ledger' : 'Hệ Thống Kế Toán (TT200)', path: '/saas/accounting', icon: Calculator },
        { name: isEn ? 'Financial Reports & P&L' : 'Báo cáo Tài chính & KQKD', path: '/saas/reports', icon: BarChart3 },
      ],
    },
    {
      title: isEn ? 'SYSTEM & ONLINE STORE' : 'HỆ THỐNG & KÊNH ONLINE',
      items: [
        { name: isEn ? 'System Settings' : 'Cài đặt Hệ thống', path: '/saas/settings', icon: Settings },
        { name: isEn ? 'WebShop Front' : 'WebShop Online', path: '/', icon: ShoppingBag },
      ],
    },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-zinc-950/60 backdrop-blur-xs lg:hidden"
          onClick={onClose}
        />
      )}

      {/* Sidebar Drawer */}
      <aside
        className={`fixed top-0 left-0 z-50 h-screen bg-zinc-900 text-zinc-100 border-r border-zinc-800 flex flex-col transition-all duration-300 ease-in-out lg:translate-x-0 ${
          isOpen ? 'translate-x-0' : '-translate-x-full'
        } ${isCollapsed ? 'lg:w-20' : 'lg:w-64'} w-64`}
      >
        {/* Brand Header */}
        <div className="h-16 px-4 border-b border-zinc-800 flex items-center justify-between">
          <div className="flex items-center gap-3 overflow-hidden">
            <div className="h-10 w-10 rounded-xl bg-amber-500 flex items-center justify-center text-zinc-950 font-bold shadow-lg shadow-amber-500/20 shrink-0">
              <Building2 className="h-5 w-5" />
            </div>
            {!isCollapsed && (
              <div className="truncate">
                <h1 className="font-bold text-base text-zinc-100 tracking-tight leading-tight truncate">
                  ERP-VIỆT SaaS
                </h1>
                <span className="text-[10px] text-amber-400 font-medium px-1.5 py-0.5 rounded-xs bg-amber-500/10 border border-amber-500/20">
                  Enterprise Cloud
                </span>
              </div>
            )}
          </div>

          {/* Desktop Toggle Button in Header */}
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex p-1.5 rounded-lg text-zinc-400 hover:text-amber-400 hover:bg-zinc-800 transition-colors"
              title={isCollapsed ? 'Mở rộng Sidebar' : 'Thu gọn Sidebar'}
            >
              <ChevronLeft className={`h-4 w-4 transition-transform duration-300 ${isCollapsed ? 'rotate-180' : ''}`} />
            </button>
          )}
        </div>

        {/* Navigation Section */}
        <div className="flex-1 overflow-y-auto px-2 py-4 space-y-6 no-scrollbar">
          {navGroups.map((group, idx) => (
            <div key={idx} className="space-y-1">
              {!isCollapsed ? (
                <h2 className="px-3 text-[10px] font-bold text-zinc-500 uppercase tracking-wider truncate">
                  {group.title}
                </h2>
              ) : (
                <div className="my-2 border-t border-zinc-800/80" />
              )}
              {group.items.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    onClick={onClose}
                    title={isCollapsed ? item.name : undefined}
                    className={({ isActive }) =>
                      `flex items-center ${
                        isCollapsed ? 'justify-center px-0 py-3' : 'justify-between px-3 py-2.5'
                      } rounded-xl text-sm font-medium transition-all ${
                        isActive
                          ? 'bg-amber-500 text-zinc-950 font-bold shadow-md shadow-amber-500/20'
                          : 'text-zinc-400 hover:text-zinc-100 hover:bg-zinc-800/60'
                      }`
                    }
                  >
                    <div className="flex items-center gap-3">
                      <Icon className="h-5 w-5 shrink-0" />
                      {!isCollapsed && <span className="truncate">{item.name}</span>}
                    </div>
                    {!isCollapsed && <ChevronRight className="h-3.5 w-3.5 opacity-40 shrink-0" />}
                  </NavLink>
                );
              })}
            </div>
          ))}
        </div>

        {/* Footer ERP Admin User Info */}
        <div className="p-3 border-t border-zinc-800 bg-zinc-950/50">
          <div className="flex items-center justify-between p-2 rounded-xl bg-zinc-800/40">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="h-8 w-8 rounded-full bg-amber-500 text-zinc-950 flex items-center justify-center font-bold text-xs shrink-0 shadow-xs">
                A
              </div>
              {!isCollapsed && (
                <div className="overflow-hidden">
                  <p className="text-xs font-bold text-zinc-200 truncate">
                    {isEn ? 'ERP Administrator' : 'Quản trị viên ERP'}
                  </p>
                  <p className="text-[10px] text-amber-400 font-medium truncate">admin@erp.vn (Admin)</p>
                </div>
              )}
            </div>
            {!isCollapsed && (
              <button
                onClick={() => {
                  logout();
                }}
                className="p-1.5 rounded-md hover:bg-zinc-800 text-zinc-400 hover:text-red-400 transition-colors shrink-0"
                title={isEn ? 'Logout ERP Account' : 'Thoát tài khoản ERP'}
              >
                <LogOut className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
};

