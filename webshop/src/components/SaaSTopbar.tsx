import React, { useState, useRef, useEffect } from 'react';
import { Menu, Bell, Sun, Moon, Plus, ShieldCheck, PanelLeftClose, PanelLeftOpen, ShoppingBag, AlertTriangle, FileText, CheckCircle2, X, ArrowRight, Globe } from 'lucide-react';
import { useTheme } from '../contexts/ThemeContext';
import { useAuth } from '../contexts/AuthContext';
import { useLanguage } from '../contexts/LanguageContext';
import { useNavigate, useLocation, Link } from 'react-router-dom';

interface SaaSTopbarProps {
  onOpenSidebar: () => void;
  title?: string;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
}

interface NotificationItem {
  id: string;
  type: 'order' | 'stock' | 'debt' | 'system';
  title: string;
  message: string;
  time: string;
  read: boolean;
  link: string;
}

export const SaaSTopbar: React.FC<SaaSTopbarProps> = ({
  onOpenSidebar,
  title = 'Tổng quan hệ thống',
  isCollapsed = false,
  onToggleCollapse,
}) => {
  const { theme, toggleTheme } = useTheme();
  const { language, toggleLanguage } = useLanguage();
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [showNotifications, setShowNotifications] = useState(false);
  const bellRef = useRef<HTMLDivElement>(null);

  const [notifications, setNotifications] = useState<NotificationItem[]>([
    {
      id: '1',
      type: 'order',
      title: 'Đơn hàng WebShop mới',
      message: 'Khách hàng Trần Thị Thu Hà vừa đặt đơn #ORD-260730-001 (19,800,000đ)',
      time: 'Vừa xong',
      read: false,
      link: '/saas/web-orders?code=ORD-260730-001',
    },
    {
      id: '2',
      type: 'stock',
      title: 'Cảnh báo hàng tồn kho',
      message: '2 sản phẩm (Áo thun polo, Giày sneaker) sắp chạm ngưỡng định mức tối thiểu',
      time: '15 phút trước',
      read: false,
      link: '/saas/inventory',
    },
    {
      id: '3',
      type: 'debt',
      title: 'Nhắc công nợ quá hạn',
      message: 'Công ty Nam Hải có khoản công nợ 15,200,000đ đến hạn thanh toán',
      time: '1 giờ trước',
      read: true,
      link: '/saas/debt',
    },
    {
      id: '4',
      type: 'system',
      title: 'Đồng bộ Python JWT Realtime',
      message: 'Hệ thống đã tự động kết nối và đồng bộ 100% chứng từ kho và kế toán',
      time: 'Hôm nay',
      read: true,
      link: '/saas/settings',
    },
  ]);

  const unreadCount = notifications.filter((n) => !n.read).length;

  const markAllAsRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
  };

  const isDashboard =
    location.pathname === '/saas' ||
    location.pathname === '/saas/' ||
    location.pathname === '/saas/dashboard';

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
        setShowNotifications(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const isEn = language === 'en';

  const displayedTitle =
    title === 'Tổng quan hệ thống'
      ? isEn
        ? 'System Overview'
        : 'Tổng quan hệ thống'
      : title;

  return (
    <header className="h-16 border-b border-zinc-200 dark:border-zinc-800 bg-white/80 dark:bg-zinc-900/80 backdrop-blur-md sticky top-0 z-30 px-4 lg:px-6 flex items-center justify-between transition-colors">
      {/* Left Section: Mobile Toggle, Desktop Collapse & Page Title */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Mobile menu trigger */}
        <button
          onClick={onOpenSidebar}
          className="p-2 rounded-lg text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 lg:hidden transition-colors cursor-pointer"
          title={isEn ? 'Open mobile menu' : 'Mở menu mobile'}
        >
          <Menu className="h-5 w-5" />
        </button>

        {/* Desktop sidebar collapse / expand button */}
        {onToggleCollapse && (
          <button
            onClick={onToggleCollapse}
            className="hidden lg:flex p-2 rounded-lg text-zinc-500 dark:text-zinc-400 hover:text-amber-500 dark:hover:text-amber-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
            title={
              isCollapsed
                ? isEn
                  ? 'Expand Sidebar'
                  : 'Mở rộng Sidebar'
                : isEn
                ? 'Collapse Sidebar'
                : 'Thu gọn Sidebar'
            }
          >
            {isCollapsed ? (
              <PanelLeftOpen className="h-5 w-5" />
            ) : (
              <PanelLeftClose className="h-5 w-5" />
            )}
          </button>
        )}

        <div>
          <h1 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            {displayedTitle}
            <span className="hidden sm:inline-flex items-center gap-1 text-[11px] font-medium px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950/50 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800">
              <ShieldCheck className="h-3 w-3" /> Realtime API JWT Connected
            </span>
          </h1>
        </div>
      </div>

      {/* Right Section: Actions & Profile */}
      <div className="flex items-center gap-2 sm:gap-3">
        {/* Language Toggle */}
        <button
          onClick={toggleLanguage}
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-semibold bg-zinc-100 dark:bg-zinc-800 text-zinc-700 dark:text-zinc-200 hover:bg-zinc-200 dark:hover:bg-zinc-700 transition-colors cursor-pointer border border-zinc-200 dark:border-zinc-700"
          title="Chuyển đổi ngôn ngữ / Switch Language"
        >
          <Globe className="h-3.5 w-3.5 text-blue-500" />
          <span className="uppercase">{language}</span>
          <span className="text-[10px] text-zinc-400">({language === 'vi' ? '🇻🇳 VN' : '🇬🇧 EN'})</span>
        </button>

        {/* Theme Toggle */}
        <button
          onClick={toggleTheme}
          className="p-2 rounded-lg text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors cursor-pointer"
          title={isEn ? 'Toggle theme' : 'Đổi giao diện'}
        >
          {theme === 'dark' ? <Sun className="h-4 w-4 text-amber-400" /> : <Moon className="h-4 w-4 text-zinc-600" />}
        </button>

        {/* Notifications Bell */}
        <div className="relative" ref={bellRef}>
          <button
            onClick={() => setShowNotifications(!showNotifications)}
            className="p-2 rounded-lg text-zinc-600 dark:text-zinc-300 hover:bg-zinc-100 dark:hover:bg-zinc-800 transition-colors relative cursor-pointer"
            title={isEn ? 'System Notifications' : 'Thông báo hệ thống'}
          >
            <Bell className="h-4 w-4" />
            {unreadCount > 0 && (
              <span className="absolute top-1 right-1 h-4 min-w-[16px] px-1 rounded-full bg-amber-500 text-zinc-950 text-[10px] font-extrabold flex items-center justify-center ring-2 ring-white dark:ring-zinc-900">
                {unreadCount}
              </span>
            )}
          </button>

          {/* Notifications Dropdown Panel */}
          {showNotifications && (
            <div className="absolute right-0 mt-2 w-80 sm:w-96 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-xl z-50 overflow-hidden animate-[fade-in_0.15s_ease-out]">
              <div className="p-3.5 border-b border-zinc-100 dark:border-zinc-800 flex items-center justify-between bg-zinc-50/50 dark:bg-zinc-800/30">
                <div className="flex items-center gap-2">
                  <Bell className="h-4 w-4 text-amber-500" />
                  <span className="text-xs font-bold text-zinc-900 dark:text-zinc-100">
                    {isEn ? 'ERP System Notifications' : 'Thông báo hệ thống ERP'}
                  </span>
                  {unreadCount > 0 && (
                    <span className="px-1.5 py-0.5 text-[10px] font-bold bg-amber-500/20 text-amber-600 dark:text-amber-400 rounded-full border border-amber-500/30">
                      {unreadCount} {isEn ? 'new' : 'mới'}
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={markAllAsRead}
                    className="text-[11px] font-semibold text-amber-600 dark:text-amber-400 hover:underline cursor-pointer"
                  >
                    {isEn ? 'Mark all as read' : 'Đánh dấu đã đọc'}
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-zinc-100 dark:divide-zinc-800/60">
                {notifications.map((item) => (
                  <div
                    key={item.id}
                    onClick={() => {
                      setNotifications((prev) =>
                        prev.map((n) => (n.id === item.id ? { ...n, read: true } : n))
                      );
                      setShowNotifications(false);
                      navigate(item.link);
                    }}
                    className={`p-3.5 hover:bg-zinc-50 dark:hover:bg-zinc-800/50 transition-colors cursor-pointer flex gap-3 items-start ${
                      !item.read ? 'bg-amber-50/40 dark:bg-amber-950/10' : ''
                    }`}
                  >
                    <div className="p-2 rounded-xl shrink-0 mt-0.5 bg-zinc-100 dark:bg-zinc-800">
                      {item.type === 'order' && <ShoppingBag className="h-4 w-4 text-amber-500" />}
                      {item.type === 'stock' && <AlertTriangle className="h-4 w-4 text-red-500" />}
                      {item.type === 'debt' && <FileText className="h-4 w-4 text-indigo-500" />}
                      {item.type === 'system' && <CheckCircle2 className="h-4 w-4 text-emerald-500" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between gap-1 mb-0.5">
                        <p className={`text-xs font-bold truncate ${!item.read ? 'text-zinc-900 dark:text-zinc-100' : 'text-zinc-700 dark:text-zinc-300'}`}>
                          {item.title}
                        </p>
                        <span className="text-[10px] text-zinc-400 shrink-0">{item.time}</span>
                      </div>
                      <p className="text-[11px] text-zinc-500 dark:text-zinc-400 line-clamp-2 leading-relaxed">
                        {item.message}
                      </p>
                    </div>
                  </div>
                ))}
              </div>

              <div className="p-2.5 bg-zinc-50 dark:bg-zinc-800/50 border-t border-zinc-100 dark:border-zinc-800 text-center">
                <Link
                  to="/saas/web-orders"
                  onClick={() => setShowNotifications(false)}
                  className="text-xs font-semibold text-amber-600 dark:text-amber-400 hover:text-amber-500 inline-flex items-center gap-1 cursor-pointer"
                >
                  <span>{isEn ? 'View all orders & alerts' : 'Xem tất cả đơn hàng & cảnh báo'}</span>
                  <ArrowRight className="h-3 w-3" />
                </Link>
              </div>
            </div>
          )}
        </div>

        {/* ERP Admin User Badge (Separate from WebShop Customer Account) */}
        <div className="pl-2 border-l border-zinc-200 dark:border-zinc-800 flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-amber-500 text-zinc-950 flex items-center justify-center font-bold text-xs shadow-xs">
            A
          </div>
          <div className="hidden sm:block text-left">
            <p className="text-xs font-bold text-zinc-900 dark:text-zinc-100 leading-tight truncate max-w-[130px]">
              {isEn ? 'ERP Administrator' : 'Quản trị viên ERP'}
            </p>
            <p className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold leading-tight flex items-center gap-1">
              <ShieldCheck className="w-3 h-3 inline" /> Admin System
            </p>
          </div>
        </div>
      </div>
    </header>
  );
};


