import React from "react";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";

// Context Providers
import { ToastProvider } from "./contexts/ToastContext";
import { AuthProvider } from "./contexts/AuthContext";
import { SaaSAuthProvider } from "./contexts/SaaSAuthContext";
import { CartProvider } from "./contexts/CartContext";
import { ThemeProvider } from "./contexts/ThemeContext";
import { LanguageProvider } from "./contexts/LanguageContext";

// Layouts
import ShopLayout from "./layouts/ShopLayout";
import SaaSLayout from "./layouts/SaaSLayout";
import ProtectedRoute from "./components/ProtectedRoute";
import SaaSProtectedRoute from "./components/SaaSProtectedRoute";

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
import { SaaSLoginPage } from "./pages/saas/SaaSLoginPage";
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
            <SaaSAuthProvider>
              <CartProvider>
                <BrowserRouter>
                  <Routes>
                    {/* ================= SaaS ERP SYSTEM LOGIN ================= */}
                    <Route path="/saas/login" element={<SaaSLoginPage />} />

                    {/* ================= SaaS ERP PROTECTED ROUTES ================= */}
                    <Route
                      path="/saas/dashboard"
                      element={
                        <SaaSProtectedRoute>
                          <SaaSLayout title="Dashboard Tổng Quan">
                            <SaaSDashboardPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/web-orders"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "SALES", "ACCOUNTANT"]}>
                          <SaaSLayout title="Quản Lý Đơn Hàng WebShop">
                            <SaaSWebOrdersPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/products"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "SALES", "WAREHOUSE", "PURCHASING"]}>
                          <SaaSLayout title="Danh Mục Hàng Hóa">
                            <SaaSProductsPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/categories-units"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "SALES"]}>
                          <SaaSLayout title="Nhóm Danh Mục & Đơn Vị Tính">
                            <SaaSCategoriesUnitsPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/customers"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "SALES"]}>
                          <SaaSLayout title="Quản Lý Khách Hàng">
                            <SaaSCustomersPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/suppliers"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "PURCHASING"]}>
                          <SaaSLayout title="Nhà Cung Cấp">
                            <SaaSSuppliersPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/warehouses"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "WAREHOUSE"]}>
                          <SaaSLayout title="Địa Điểm Kho Bãi & Tồn Đầu Kỳ">
                            <SaaSWarehousesPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/stock-in"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "WAREHOUSE", "PURCHASING"]}>
                          <SaaSLayout title="Phiếu Nhập Kho">
                            <SaaSStockInPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/stock-out"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "WAREHOUSE"]}>
                          <SaaSLayout title="Phiếu Xuất Kho & Bán Hàng">
                            <SaaSStockOutPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/stocktaking"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "WAREHOUSE"]}>
                          <SaaSLayout title="Kiểm Kê Kho & Lệch Kho">
                            <SaaSStocktakingPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/quotations"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "SALES"]}>
                          <SaaSLayout title="Báo Giá Thương Mại">
                            <SaaSQuotationsPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/inventory"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "WAREHOUSE"]}>
                          <SaaSLayout title="Báo Cáo Tồn Kho">
                            <SaaSInventoryPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/debt"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "ACCOUNTANT"]}>
                          <SaaSLayout title="Sổ Công Nợ & Thu Chi">
                            <SaaSDebtPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/vat"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "ACCOUNTANT"]}>
                          <SaaSLayout title="Kê Khai Thuế GTGT (VAT)">
                            <SaaSVATPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/accounting"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "ACCOUNTANT"]}>
                          <SaaSLayout title="Hệ Thống Kế Toán Doanh Nghiệp">
                            <SaaSAccountingPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/reports"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN", "ACCOUNTANT"]}>
                          <SaaSLayout title="Báo Cáo Tài Chính & KQKD">
                            <SaaSReportsPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
                      }
                    />
                    <Route
                      path="/saas/settings"
                      element={
                        <SaaSProtectedRoute allowedRoles={["ADMIN"]}>
                          <SaaSLayout title="Cài Đặt Hệ Thống">
                            <SaaSSettingsPage />
                          </SaaSLayout>
                        </SaaSProtectedRoute>
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
            </SaaSAuthProvider>
          </AuthProvider>
        </ToastProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
}

