import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

// Context Providers
import { ToastProvider } from "./contexts/ToastContext";
import { AuthProvider } from "./contexts/AuthContext";
import { CartProvider } from "./contexts/CartContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { LanguageProvider } from "./contexts/LanguageContext";

// Layouts
import ShopLayout from "./layouts/ShopLayout";
import SaaSLayout from "./layouts/SaaSLayout";
import ProtectedRoute from "./components/ProtectedRoute";

// WebShop E-Commerce Pages
import CatalogPage from "./pages/CatalogPage";
import ProductPage from "./pages/ProductPage";
import CartPage from "./pages/CartPage";
import CheckoutPage from "./pages/CheckoutPage";
import OrderSuccessPage from "./pages/OrderSuccessPage";
import OrdersPage from "./pages/OrdersPage";
import OrderDetailPage from "./pages/OrderDetailPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import GoogleCallbackPage from "./pages/GoogleCallbackPage";
import AccountPage from "./pages/AccountPage";

// SaaS ERP Enterprise Pages
import { SaaSDashboardPage } from "./pages/saas/SaaSDashboardPage";
import { SaaSWebOrdersPage } from "./pages/saas/SaaSWebOrdersPage";
import { SaaSProductsPage } from "./pages/saas/SaaSProductsPage";
import { SaaSCategoriesUnitsPage } from "./pages/saas/SaaSCategoriesUnitsPage";
import { SaaSCustomersPage } from "./pages/saas/SaaSCustomersPage";
import { SaaSSuppliersPage } from "./pages/saas/SaaSSuppliersPage";
import { SaaSWarehousesPage } from "./pages/saas/SaaSWarehousesPage";
import { SaaSStockInPage } from "./pages/saas/SaaSStockInPage";
import { SaaSStockOutPage } from "./pages/saas/SaaSStockOutPage";
import { SaaSStocktakingPage } from "./pages/saas/SaaSStocktakingPage";
import { SaaSQuotationsPage } from "./pages/saas/SaaSQuotationsPage";
import { SaaSInventoryPage } from "./pages/saas/SaaSInventoryPage";
import { SaaSDebtPage } from "./pages/saas/SaaSDebtPage";
import { SaaSVATPage } from "./pages/saas/SaaSVATPage";
import { SaaSAccountingPage } from "./pages/saas/SaaSAccountingPage";
import { SaaSReportsPage } from "./pages/saas/SaaSReportsPage";
import { SaaSSettingsPage } from "./pages/saas/SaaSSettingsPage";

export default function App() {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <ToastProvider>
        <AuthProvider>
          <CartProvider>
            <BrowserRouter>
              <Routes>
                {/* ================= SaaS ERP SYSTEM ROUTES ================= */}
                <Route
                  path="/saas/dashboard"
                  element={
                    <SaaSLayout title="Dashboard Tổng Quan">
                      <SaaSDashboardPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/web-orders"
                  element={
                    <SaaSLayout title="Quản Lý Đơn Hàng WebShop">
                      <SaaSWebOrdersPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/products"
                  element={
                    <SaaSLayout title="Danh Mục Hàng Hóa">
                      <SaaSProductsPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/categories-units"
                  element={
                    <SaaSLayout title="Nhóm Danh Mục & Đơn Vị Tính">
                      <SaaSCategoriesUnitsPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/customers"
                  element={
                    <SaaSLayout title="Quản Lý Khách Hàng">
                      <SaaSCustomersPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/suppliers"
                  element={
                    <SaaSLayout title="Nhà Cung Cấp">
                      <SaaSSuppliersPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/warehouses"
                  element={
                    <SaaSLayout title="Địa Điểm Kho Bãi & Tồn Đầu Kỳ">
                      <SaaSWarehousesPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/stock-in"
                  element={
                    <SaaSLayout title="Phiếu Nhập Kho">
                      <SaaSStockInPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/stock-out"
                  element={
                    <SaaSLayout title="Phiếu Xuất Kho & Bán Hàng">
                      <SaaSStockOutPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/stocktaking"
                  element={
                    <SaaSLayout title="Kiểm Kê Kho & Lệch Kho">
                      <SaaSStocktakingPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/quotations"
                  element={
                    <SaaSLayout title="Báo Giá Thương Mại">
                      <SaaSQuotationsPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/inventory"
                  element={
                    <SaaSLayout title="Báo Cáo Tồn Kho">
                      <SaaSInventoryPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/debt"
                  element={
                    <SaaSLayout title="Sổ Công Nợ & Thu Chi">
                      <SaaSDebtPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/vat"
                  element={
                    <SaaSLayout title="Kê Khai Thuế GTGT (VAT)">
                      <SaaSVATPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/accounting"
                  element={
                    <SaaSLayout title="Hệ Thống Kế Toán Doanh Nghiệp">
                      <SaaSAccountingPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/reports"
                  element={
                    <SaaSLayout title="Báo Cáo Tài Chính & KQKD">
                      <SaaSReportsPage />
                    </SaaSLayout>
                  }
                />
                <Route
                  path="/saas/settings"
                  element={
                    <SaaSLayout title="Cài Đặt Hệ Thống">
                      <SaaSSettingsPage />
                    </SaaSLayout>
                  }
                />
                <Route path="/saas" element={<Navigate to="/saas/dashboard" replace />} />

                {/* ================= WEBSHOP STOREFRONT ROUTES ================= */}
                <Route
                  path="/*"
                  element={
                    <ShopLayout>
                      <Routes>
                        <Route path="/" element={<CatalogPage />} />
                        <Route path="/product/:slug" element={<ProductPage />} />
                        <Route path="/cart" element={<CartPage />} />
                        <Route path="/checkout" element={<CheckoutPage />} />
                        <Route path="/order-success/:code" element={<OrderSuccessPage />} />
                        <Route path="/login" element={<LoginPage />} />
                        <Route path="/register" element={<RegisterPage />} />
                        <Route path="/auth/google/callback" element={<GoogleCallbackPage />} />

                        <Route
                          path="/orders"
                          element={
                            <ProtectedRoute>
                              <OrdersPage />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/orders/:code"
                          element={
                            <ProtectedRoute>
                              <OrderDetailPage />
                            </ProtectedRoute>
                          }
                        />
                        <Route
                          path="/account"
                          element={
                            <ProtectedRoute>
                              <AccountPage />
                            </ProtectedRoute>
                          }
                        />
                        <Route path="*" element={<Navigate to="/" replace />} />
                      </Routes>
                    </ShopLayout>
                  }
                />
              </Routes>
            </BrowserRouter>
          </CartProvider>
        </AuthProvider>
      </ToastProvider>
    </LanguageProvider>
  </ThemeProvider>
  );
}
