import React, { useState } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { ArrowDownLeft, Plus, CheckCircle2, Clock, Printer, Edit2, Trash2, X, FileText, Calculator } from 'lucide-react';
import { DataTable } from '../../components/DataTable';
import { SaaSPrintModal } from '../../components/SaaSPrintModal';
import { SaaSDateFilterBar, DateFilterValue, filterByDateRange } from '../../components/SaaSDateFilterBar';
import { SearchableSelect, SelectOption } from '../../components/SearchableSelect';
import { useToast } from '../../contexts/ToastContext';
import { generateERPCode } from '../../utils/format';

interface StockInLineItem {
  id: string;
  productId: string;
  productName: string;
  sku: string;
  unit: string;
  quantity: number;
  unitPrice: number;
  vatRate: number;
}

interface StockInVoucher {
  id: number;
  code: string;
  date: string;
  supplierId: string;
  supplierName: string;
  supplierPhone: string;
  supplierAddress: string;
  warehouse: string;
  invoiceNo: string;
  invoiceSeries: string;
  note: string;
  vatMode: 'grouped' | 'per_item';
  vatRateGrouped: number;
  items: StockInLineItem[];
  subtotal: number;
  vatAmount: number;
  totalAmount: number;
  status: 'Đã hoàn thành' | 'Nháp' | 'Đã hủy';
  createdBy: string;
}

const SAMPLE_PRODUCTS = [
  { id: 'p1', name: 'Giấy A4 Double A 70gsm (Ream 500 tờ)', sku: 'VT001', unit: 'Ream', price: 52000 },
  { id: 'p2', name: 'Bìa thái A4 400G (Tệp 100 tờ)', sku: 'VT002', unit: 'Tệp', price: 95000 },
  { id: 'p3', name: 'Mực in Canon 2900 12A Cartridge', sku: 'VT003', unit: 'Hộp', price: 280000 },
  { id: 'p4', name: 'Màn Hình LG UltraGear 27 inch 144Hz', sku: 'SP002', unit: 'Cái', price: 4900000 },
];

const SAMPLE_SUPPLIERS = [
  { id: 's1', name: 'Tổng Công Ty Giấy & Bao Bì Double A Việt Nam', phone: '0912 345 678', address: 'KCN Sài Đồng, Long Biên, Hà Nội' },
  { id: 's2', name: 'Nhà Phân Phối Linh Kiện Máy Tính SPC', phone: '0988 111 222', address: 'Số 44 Phố Vĩnh Tuy, Q. Hai Bà Trưng, Hà Nội' },
  { id: 's3', name: 'Công ty Cổ Phần Thiết Bị Văn Phòng Hải Hà', phone: '0903 888 999', address: 'KCN Từ Liêm, Q. Nam Từ Liêm, Hà Nội' },
];

export const SaaSStockInPage: React.FC = () => {
  const { addToast } = useToast();
  const [dateFilter, setDateFilter] = useState<DateFilterValue>({ preset: 'all', fromDate: '', toDate: '' });

  const [stockIns, setStockIns] = useState<StockInVoucher[]>([
    {
      id: 1,
      code: 'PN-260730-001',
      date: '2026-07-28 09:30',
      supplierId: 's1',
      supplierName: 'Tổng Công Ty Giấy & Bao Bì Double A Việt Nam',
      supplierPhone: '0912 345 678',
      supplierAddress: 'KCN Sài Đồng, Long Biên, Hà Nội',
      warehouse: 'Kho Chính - Hà Nội',
      invoiceNo: '0008891',
      invoiceSeries: 'C26MH',
      note: 'Nhập kho lô giấy in văn phòng quý 3',
      vatMode: 'grouped',
      vatRateGrouped: 8,
      items: [
        {
          id: '1',
          productId: 'p1',
          productName: 'Giấy A4 Double A 70gsm (Ream 500 tờ)',
          sku: 'VT001',
          unit: 'Ream',
          quantity: 500,
          unitPrice: 52000,
          vatRate: 8,
        },
      ],
      subtotal: 26000000,
      vatAmount: 2080000,
      totalAmount: 28080000,
      status: 'Đã hoàn thành',
      createdBy: 'Nguyễn Văn Khách',
    },
    {
      id: 2,
      code: 'PN-260730-002',
      date: '2026-07-29 14:15',
      supplierId: 's2',
      supplierName: 'Nhà Phân Phối Linh Kiện Máy Tính SPC',
      supplierPhone: '0988 111 222',
      supplierAddress: 'Số 44 Phố Vĩnh Tuy, Q. Hai Bà Trưng, Hà Nội',
      warehouse: 'Kho Chính - Hà Nội',
      invoiceNo: '0008892',
      invoiceSeries: 'C26MH',
      note: 'Nhập màn hình LG phục vụ đơn hàng bán buôn',
      vatMode: 'grouped',
      vatRateGrouped: 10,
      items: [
        {
          id: '1',
          productId: 'p4',
          productName: 'Màn Hình LG UltraGear 27 inch 144Hz',
          sku: 'SP002',
          unit: 'Cái',
          quantity: 20,
          unitPrice: 4900000,
          vatRate: 10,
        },
      ],
      subtotal: 98000000,
      vatAmount: 9800000,
      totalAmount: 107800000,
      status: 'Đã hoàn thành',
      createdBy: 'Lê Quản Kho',
    },
  ]);

  const [printModalOpen, setPrintModalOpen] = useState(false);
  const [selectedStockIn, setSelectedStockIn] = useState<StockInVoucher | null>(null);

  // Voucher Form Modal state
  const [showVoucherModal, setShowVoucherModal] = useState(false);
  const [editingVoucher, setEditingVoucher] = useState<StockInVoucher | null>(null);

  const [voucherForm, setVoucherForm] = useState({
    code: '',
    date: new Date().toISOString().slice(0, 10),
    supplierId: 's1',
    warehouse: 'Kho Chính - Hà Nội',
    invoiceNo: '',
    invoiceSeries: 'C26MH',
    note: '',
    vatMode: 'grouped' as 'grouped' | 'per_item',
    vatRateGrouped: 10,
    status: 'Đã hoàn thành' as 'Nháp' | 'Đã hoàn thành',
  });

  const [lineItems, setLineItems] = useState<StockInLineItem[]>([
    {
      id: 'item-1',
      productId: 'p1',
      productName: 'Giấy A4 Double A 70gsm (Ream 500 tờ)',
      sku: 'VT001',
      unit: 'Ream',
      quantity: 100,
      unitPrice: 52000,
      vatRate: 8,
    },
  ]);

  const handleOpenPrint = (item: StockInVoucher) => {
    setSelectedStockIn(item);
    setPrintModalOpen(true);
  };

  const handleOpenAddVoucher = () => {
    setEditingVoucher(null);
    const nextCode = generateERPCode('PN', stockIns.length + 1);
    setVoucherForm({
      code: nextCode,
      date: new Date().toISOString().slice(0, 10),
      supplierId: 's1',
      warehouse: 'Kho Chính - Hà Nội',
      invoiceNo: '',
      invoiceSeries: 'C26MH',
      note: '',
      vatMode: 'grouped',
      vatRateGrouped: 10,
      status: 'Đã hoàn thành',
    });
    setLineItems([
      {
        id: `item-${Date.now()}`,
        productId: 'p1',
        productName: 'Giấy A4 Double A 70gsm (Ream 500 tờ)',
        sku: 'VT001',
        unit: 'Ream',
        quantity: 100,
        unitPrice: 52000,
        vatRate: 8,
      },
    ]);
    setShowVoucherModal(true);
  };

  const handleOpenEditVoucher = (v: StockInVoucher) => {
    setEditingVoucher(v);
    setVoucherForm({
      code: v.code,
      date: v.date.split(' ')[0],
      supplierId: v.supplierId,
      warehouse: v.warehouse,
      invoiceNo: v.invoiceNo,
      invoiceSeries: v.invoiceSeries,
      note: v.note,
      vatMode: v.vatMode,
      vatRateGrouped: v.vatRateGrouped,
      status: v.status === 'Đã hủy' ? 'Nháp' : v.status,
    });
    setLineItems(v.items.length > 0 ? v.items : []);
    setShowVoucherModal(true);
  };

  const handleAddLineItem = () => {
    const defaultProd = SAMPLE_PRODUCTS[0];
    const newItem: StockInLineItem = {
      id: `item-${Date.now()}`,
      productId: defaultProd.id,
      productName: defaultProd.name,
      sku: defaultProd.sku,
      unit: defaultProd.unit,
      quantity: 10,
      unitPrice: defaultProd.price,
      vatRate: 10,
    };
    setLineItems([...lineItems, newItem]);
  };

  const handleRemoveLineItem = (id: string) => {
    if (lineItems.length <= 1) {
      addToast('Phiếu nhập kho phải có ít nhất 1 mặt hàng!', 'warning');
      return;
    }
    setLineItems(lineItems.filter((item) => item.id !== id));
  };

  const handleProductChange = (lineId: string, productId: string) => {
    const prod = SAMPLE_PRODUCTS.find((p) => p.id === productId);
    if (!prod) return;
    setLineItems(
      lineItems.map((item) =>
        item.id === lineId
          ? {
              ...item,
              productId: prod.id,
              productName: prod.name,
              sku: prod.sku,
              unit: prod.unit,
              unitPrice: prod.price,
            }
          : item
      )
    );
  };

  const handleLineChange = (lineId: string, field: keyof StockInLineItem, value: any) => {
    setLineItems(
      lineItems.map((item) => (item.id === lineId ? { ...item, [field]: value } : item))
    );
  };

  const calcSubtotal = lineItems.reduce((acc, item) => acc + item.quantity * item.unitPrice, 0);

  const calcVatAmount = () => {
    if (voucherForm.vatMode === 'grouped') {
      return (calcSubtotal * voucherForm.vatRateGrouped) / 100;
    } else {
      return lineItems.reduce(
        (acc, item) => acc + (item.quantity * item.unitPrice * (item.vatRate || 0)) / 100,
        0
      );
    }
  };

  const calcTotalAmount = calcSubtotal + calcVatAmount();

  const handleSaveVoucher = (e: React.FormEvent) => {
    e.preventDefault();
    if (lineItems.length === 0) {
      addToast('Vui lòng thêm ít nhất 1 hàng hóa vào phiếu nhập!', 'error');
      return;
    }

    const supp = SAMPLE_SUPPLIERS.find((s) => s.id === voucherForm.supplierId) || SAMPLE_SUPPLIERS[0];

    const sub = calcSubtotal;
    const vat = calcVatAmount();
    const total = calcTotalAmount;

    if (editingVoucher) {
      setStockIns(
        stockIns.map((v) =>
          v.id === editingVoucher.id
            ? {
                ...v,
                code: voucherForm.code,
                date: `${voucherForm.date} ${new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`,
                supplierId: supp.id,
                supplierName: supp.name,
                supplierPhone: supp.phone,
                supplierAddress: supp.address,
                warehouse: voucherForm.warehouse,
                invoiceNo: voucherForm.invoiceNo,
                invoiceSeries: voucherForm.invoiceSeries,
                note: voucherForm.note,
                vatMode: voucherForm.vatMode,
                vatRateGrouped: voucherForm.vatRateGrouped,
                items: lineItems,
                subtotal: sub,
                vatAmount: vat,
                totalAmount: total,
                status: voucherForm.status,
              }
            : v
        )
      );
      addToast(`Đã cập nhật phiếu nhập kho "${voucherForm.code}" thành công!`, 'success');
    } else {
      const newVoucher: StockInVoucher = {
        id: Date.now(),
        code: voucherForm.code,
        date: `${voucherForm.date} ${new Date().toLocaleTimeString('vi-VN', { hour: '2-digit', minute: '2-digit' })}`,
        supplierId: supp.id,
        supplierName: supp.name,
        supplierPhone: supp.phone,
        supplierAddress: supp.address,
        warehouse: voucherForm.warehouse,
        invoiceNo: voucherForm.invoiceNo,
        invoiceSeries: voucherForm.invoiceSeries,
        note: voucherForm.note,
        vatMode: voucherForm.vatMode,
        vatRateGrouped: voucherForm.vatRateGrouped,
        items: lineItems,
        subtotal: sub,
        vatAmount: vat,
        totalAmount: total,
        status: voucherForm.status,
        createdBy: 'SaaS Admin',
      };
      setStockIns([newVoucher, ...stockIns]);
      addToast(`Đã lập phiếu nhập kho mới "${newVoucher.code}" thành công!`, 'success');
    }
    setShowVoucherModal(false);
  };

  const handleDeleteVoucher = (id: number, code: string) => {
    if (window.confirm(`Bạn có chắc muốn xóa phiếu nhập kho "${code}"?`)) {
      setStockIns(stockIns.filter((s) => s.id !== id));
      addToast(`Đã xóa phiếu nhập kho "${code}"`, 'warning');
    }
  };

  const columns: ColumnDef<StockInVoucher>[] = [
    {
      accessorKey: 'code',
      header: 'Mã Phiếu Nhập',
      cell: ({ row, getValue }) => (
        <button
          onClick={() => handleOpenPrint(row.original)}
          className="font-mono text-xs font-bold text-emerald-600 dark:text-emerald-400 hover:underline hover:text-emerald-700 dark:hover:text-emerald-300 transition-colors cursor-pointer p-0 bg-transparent inline-flex items-center gap-1"
          title="Click vào mã phiếu để xem chi tiết / in chứng từ"
        >
          {getValue() as string}
        </button>
      ),
    },
    {
      accessorKey: 'date',
      header: 'Thời Gian',
      cell: (info) => <span className="text-xs text-zinc-600 dark:text-zinc-400">{info.getValue() as string}</span>,
    },
    {
      accessorKey: 'supplierName',
      header: 'Nhà Cung Cấp',
      cell: (info) => <span className="font-semibold text-zinc-900 dark:text-zinc-100">{info.getValue() as string}</span>,
    },
    {
      accessorKey: 'warehouse',
      header: 'Kho Nhập',
    },
    {
      accessorKey: 'totalAmount',
      header: 'Giá Trị Lô Hàng (Cả VAT)',
      cell: (info) => (
        <span className="font-bold text-zinc-900 dark:text-zinc-100">
          {(info.getValue() as number).toLocaleString('vi-VN')} đ
        </span>
      ),
    },
    {
      accessorKey: 'status',
      header: 'Trạng Thái',
      cell: (info) => (
        <span className="text-xs font-bold inline-flex items-center gap-1 text-emerald-600 dark:text-emerald-400">
          <CheckCircle2 className="h-3.5 w-3.5" /> {info.getValue() as string}
        </span>
      ),
    },
    {
      id: 'actions',
      header: 'Thao Tác',
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleOpenPrint(row.original)}
            className="p-1.5 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-300 transition-colors"
            title="In Phiếu Nhập Kho Chuẩn"
          >
            <Printer className="h-4 w-4 text-emerald-600" />
          </button>
          <button
            onClick={() => handleOpenEditVoucher(row.original)}
            className="p-1.5 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-300 transition-colors"
            title="Chỉnh sửa phiếu nhập"
          >
            <Edit2 className="h-4 w-4 text-amber-500" />
          </button>
          <button
            onClick={() => handleDeleteVoucher(row.original.id, row.original.code)}
            className="p-1.5 rounded-md hover:bg-red-50 dark:hover:bg-red-950/40 text-red-600 dark:text-red-400 transition-colors"
            title="Xóa phiếu"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  const filteredStockIns = filterByDateRange(stockIns, dateFilter);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <ArrowDownLeft className="h-6 w-6 text-emerald-500" /> Quản Lý Phiếu Nhập Kho & Chứng Từ Mua Hàng (ERP)
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Nghiệp vụ lập phiếu nhập kho hàng mua, cộng dồn tồn kho tự động, quản lý VAT đầu vào và in chứng từ giao nhận.
          </p>
        </div>

        <button
          onClick={handleOpenAddVoucher}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white shadow-xs transition-all"
        >
          <Plus className="h-4 w-4" /> Tạo phiếu nhập mới
        </button>
      </div>

      <SaaSDateFilterBar onFilterChange={(val) => setDateFilter(val)} />

      <DataTable columns={columns} data={filteredStockIns} searchPlaceholder="Tìm mã phiếu nhập, tên nhà cung cấp..." />

      {/* Print Modal */}
      {selectedStockIn && (
        <SaaSPrintModal
          isOpen={printModalOpen}
          onClose={() => setPrintModalOpen(false)}
          docType="stock_in"
          docCode={selectedStockIn.code}
          docDate={selectedStockIn.date}
          partnerName={selectedStockIn.supplierName}
          partnerAddress={selectedStockIn.supplierAddress}
          partnerPhone={selectedStockIn.supplierPhone}
          items={selectedStockIn.items.map((i) => ({
            sku: i.sku,
            name: i.productName,
            unit: i.unit,
            quantity: i.quantity,
            unitPrice: i.unitPrice,
            amount: i.quantity * i.unitPrice,
          }))}
          totalAmount={selectedStockIn.subtotal}
          taxAmount={selectedStockIn.vatAmount}
          grandTotal={selectedStockIn.totalAmount}
          notes={selectedStockIn.note || `Giao nhận tại kho: ${selectedStockIn.warehouse}`}
        />
      )}

      {/* Stock In Voucher Form Modal */}
      {showVoucherModal && (
        <div className="fixed inset-0 z-50 bg-zinc-950/70 backdrop-blur-xs flex items-center justify-center p-2 sm:p-4 overflow-y-auto">
          <div className="bg-white dark:bg-zinc-900 rounded-2xl max-w-5xl w-full my-auto p-4 sm:p-6 border border-zinc-200 dark:border-zinc-800 shadow-2xl space-y-5 max-h-[95vh] flex flex-col">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3">
              <div className="flex items-center gap-2">
                <FileText className="h-5 w-5 text-emerald-500" />
                <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100">
                  {editingVoucher ? `Chỉnh Sửa Phiếu Nhập Kho: ${editingVoucher.code}` : 'Lập Phiếu Nhập Kho Mua Hàng Mới'}
                </h3>
              </div>
              <button
                onClick={() => setShowVoucherModal(false)}
                className="p-1.5 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400 hover:text-zinc-600 dark:hover:text-zinc-200"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSaveVoucher} className="space-y-5 overflow-y-auto pr-1 flex-1">
              <div className="p-4 bg-zinc-50 dark:bg-zinc-950/60 rounded-xl border border-zinc-200/80 dark:border-zinc-800 space-y-3">
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 text-xs">
                  <div>
                    <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                      Mã Phiếu Nhập *
                    </label>
                    <input
                      type="text"
                      required
                      value={voucherForm.code}
                      onChange={(e) => setVoucherForm({ ...voucherForm, code: e.target.value })}
                      className="w-full px-3 py-2 font-mono font-bold bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                      Ngày Nhập Kho *
                    </label>
                    <input
                      type="date"
                      required
                      value={voucherForm.date}
                      onChange={(e) => setVoucherForm({ ...voucherForm, date: e.target.value })}
                      className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                      Kho Tiếp Nhận *
                    </label>
                    <SearchableSelect
                      value={voucherForm.warehouse}
                      onChange={(val) => setVoucherForm({ ...voucherForm, warehouse: val })}
                      placeholder="Chọn kho tiếp nhận..."
                      options={[
                        { value: 'Kho Chính - Hà Nội', label: 'Kho Chính - Hà Nội', code: 'K01' },
                        { value: 'Kho Phụ - TP. Hồ Chí Minh', label: 'Kho Phụ - TP. Hồ Chí Minh', code: 'K02' },
                        { value: 'Kho Hải Phòng', label: 'Kho Hải Phòng', code: 'K03' },
                      ]}
                    />
                  </div>

                  <div>
                    <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                      Nhà Cung Cấp * (Fast Search)
                    </label>
                    <SearchableSelect
                      value={voucherForm.supplierId}
                      onChange={(val) => setVoucherForm({ ...voucherForm, supplierId: val })}
                      placeholder="Tìm NCC theo tên, mã, MST..."
                      options={SAMPLE_SUPPLIERS.map((s) => ({
                        value: s.id,
                        label: s.name,
                        code: s.id.toUpperCase(),
                        subLabel: `SĐT: ${s.phone} - ${s.address}`,
                      }))}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div>
                    <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                      Số Hóa Đơn Mua Hàng & Ký Hiệu
                    </label>
                    <div className="flex gap-2">
                      <input
                        type="text"
                        placeholder="Số HĐ mua"
                        value={voucherForm.invoiceNo}
                        onChange={(e) => setVoucherForm({ ...voucherForm, invoiceNo: e.target.value })}
                        className="w-2/3 px-3 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                      />
                      <input
                        type="text"
                        placeholder="Ký hiệu"
                        value={voucherForm.invoiceSeries}
                        onChange={(e) => setVoucherForm({ ...voucherForm, invoiceSeries: e.target.value })}
                        className="w-1/3 px-3 py-2 font-mono bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                      />
                    </div>
                  </div>

                  <div className="sm:col-span-2">
                    <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                      Diễn Giải / Diễn Diễn Nhập Kho
                    </label>
                    <input
                      type="text"
                      placeholder="Mô tả hóa đơn mua hàng, phiếu nhập vật tư..."
                      value={voucherForm.note}
                      onChange={(e) => setVoucherForm({ ...voucherForm, note: e.target.value })}
                      className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                    />
                  </div>
                </div>

                {/* VAT Setup */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2 border-t border-zinc-200 dark:border-zinc-800 text-xs">
                  <div>
                    <label className="block font-semibold text-emerald-600 dark:text-emerald-400 mb-1">
                      Phương Thức VAT Đầu Vào
                    </label>
                    <div className="flex items-center gap-4 py-1">
                      <label className="inline-flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="radio"
                          name="vatModeIn"
                          value="grouped"
                          checked={voucherForm.vatMode === 'grouped'}
                          onChange={() => setVoucherForm({ ...voucherForm, vatMode: 'grouped' })}
                          className="text-emerald-500 focus:ring-emerald-500"
                        />
                        <span>VAT gộp phiếu</span>
                      </label>
                      <label className="inline-flex items-center gap-1.5 cursor-pointer">
                        <input
                          type="radio"
                          name="vatModeIn"
                          value="per_item"
                          checked={voucherForm.vatMode === 'per_item'}
                          onChange={() => setVoucherForm({ ...voucherForm, vatMode: 'per_item' })}
                          className="text-emerald-500 focus:ring-emerald-500"
                        />
                        <span>VAT theo từng dòng</span>
                      </label>
                    </div>
                  </div>

                  {voucherForm.vatMode === 'grouped' && (
                    <div>
                      <label className="block font-semibold text-zinc-700 dark:text-zinc-300 mb-1">
                        Tỷ Lệ VAT Gộp (%)
                      </label>
                      <select
                        value={voucherForm.vatRateGrouped}
                        onChange={(e) => setVoucherForm({ ...voucherForm, vatRateGrouped: Number(e.target.value) })}
                        className="w-full px-3 py-2 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                      >
                        <option value={0}>0%</option>
                        <option value={5}>5%</option>
                        <option value={8}>8% (Giảm thuế VAT)</option>
                        <option value={10}>10%</option>
                      </select>
                    </div>
                  )}
                </div>
              </div>

              {/* Items Table */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                    <Calculator className="h-4 w-4 text-emerald-500" />
                    Chi Tiết Mặt Hàng Nhập Kho ({lineItems.length} dòng)
                  </h4>
                  <button
                    type="button"
                    onClick={handleAddLineItem}
                    className="inline-flex items-center gap-1 px-3 py-1 text-xs font-bold bg-emerald-600 hover:bg-emerald-700 text-white rounded-lg transition-colors"
                  >
                    <Plus className="h-3.5 w-3.5" /> Thêm dòng nhập
                  </button>
                </div>

                <div className="border border-zinc-200 dark:border-zinc-800 rounded-xl overflow-x-auto">
                  <table className="w-full text-xs text-left">
                    <thead className="bg-zinc-100 dark:bg-zinc-800/80 text-zinc-700 dark:text-zinc-300 font-semibold">
                      <tr>
                        <th className="p-2 w-10 text-center">STT</th>
                        <th className="p-2 min-w-[200px]">Mặt Hàng Nhập *</th>
                        <th className="p-2 w-24 text-right">Số Lượng</th>
                        <th className="p-2 w-20 text-center">ĐVT</th>
                        <th className="p-2 w-32 text-right">Đơn Giá Nhập</th>
                        {voucherForm.vatMode === 'per_item' && <th className="p-2 w-20 text-center">VAT %</th>}
                        <th className="p-2 w-36 text-right">Thành Tiền</th>
                        <th className="p-2 w-10 text-center"></th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-zinc-200 dark:divide-zinc-800">
                      {lineItems.map((item, idx) => {
                        const lineSubtotal = item.quantity * item.unitPrice;
                        return (
                          <tr key={item.id} className="hover:bg-zinc-50/50 dark:hover:bg-zinc-900/50">
                            <td className="p-2 text-center text-zinc-500">{idx + 1}</td>
                            <td className="p-2 min-w-[220px]">
                              <SearchableSelect
                                value={item.productId}
                                onChange={(val) => handleProductChange(item.id, val)}
                                placeholder="Gõ tên hoặc SKU để tìm nhanh..."
                                options={SAMPLE_PRODUCTS.map((p) => ({
                                  value: p.id,
                                  label: p.name,
                                  code: p.sku,
                                  badge: `${p.price.toLocaleString('vi-VN')} đ/${p.unit}`,
                                }))}
                              />
                            </td>
                            <td className="p-2">
                              <input
                                type="number"
                                min={1}
                                value={item.quantity}
                                onChange={(e) => handleLineChange(item.id, 'quantity', Number(e.target.value))}
                                className="w-full px-2 py-1 text-right font-bold bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded"
                              />
                            </td>
                            <td className="p-2 text-center font-semibold text-zinc-600 dark:text-zinc-400">
                              {item.unit}
                            </td>
                            <td className="p-2">
                              <input
                                type="number"
                                value={item.unitPrice}
                                onChange={(e) => handleLineChange(item.id, 'unitPrice', Number(e.target.value))}
                                className="w-full px-2 py-1 text-right font-mono font-semibold bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded"
                              />
                            </td>
                            {voucherForm.vatMode === 'per_item' && (
                              <td className="p-2">
                                <select
                                  value={item.vatRate}
                                  onChange={(e) => handleLineChange(item.id, 'vatRate', Number(e.target.value))}
                                  className="w-full px-1 py-1 text-center bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-700 rounded"
                                >
                                  <option value={0}>0%</option>
                                  <option value={5}>5%</option>
                                  <option value={8}>8%</option>
                                  <option value={10}>10%</option>
                                </select>
                              </td>
                            )}
                            <td className="p-2 text-right font-mono font-bold text-zinc-900 dark:text-zinc-100">
                              {lineSubtotal.toLocaleString('vi-VN')} đ
                            </td>
                            <td className="p-2 text-center">
                              <button
                                type="button"
                                onClick={() => handleRemoveLineItem(item.id)}
                                className="p-1 hover:bg-red-50 dark:hover:bg-red-950/40 text-red-600 rounded transition-colors"
                              >
                                <Trash2 className="h-4 w-4" />
                              </button>
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Total Summary Footer */}
              <div className="flex flex-col sm:flex-row items-end justify-between p-4 bg-emerald-50/50 dark:bg-emerald-950/20 border border-emerald-200/80 dark:border-emerald-900/50 rounded-xl gap-4">
                <div className="text-xs text-zinc-500 dark:text-zinc-400 space-y-1">
                  <p className="font-semibold text-zinc-700 dark:text-zinc-300">Ghi nhận tài chính & kho bãi:</p>
                  <p>• Phiếu nhập hoàn thành sẽ tăng tồn kho tương ứng tại kho tiếp nhận.</p>
                  <p>• Thuế VAT đầu vào sẽ được tổng hợp tự động vào bảng phân bổ thuế.</p>
                </div>

                <div className="text-right space-y-1 text-xs w-full sm:w-auto min-w-[240px]">
                  <div className="flex justify-between items-center text-zinc-600 dark:text-zinc-400">
                    <span>Tổng tiền hàng mua:</span>
                    <span className="font-mono font-semibold">{calcSubtotal.toLocaleString('vi-VN')} đ</span>
                  </div>
                  <div className="flex justify-between items-center text-zinc-600 dark:text-zinc-400">
                    <span>Tiền thuế VAT đầu vào:</span>
                    <span className="font-mono font-semibold text-emerald-600 dark:text-emerald-400">
                      +{calcVatAmount().toLocaleString('vi-VN')} đ
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-sm font-bold text-zinc-900 dark:text-zinc-100 pt-1 border-t border-emerald-200 dark:border-emerald-800">
                    <span>Tổng thanh toán NCC:</span>
                    <span className="font-mono text-base text-emerald-600 dark:text-emerald-400">
                      {calcTotalAmount.toLocaleString('vi-VN')} đ
                    </span>
                  </div>
                </div>
              </div>

              {/* Form Action Buttons */}
              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setShowVoucherModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-lg shadow-xs"
                >
                  {editingVoucher ? 'Cập Nhật Phiếu Nhập' : 'Xác Nhận Nhập Kho & Lưu Lô Hàng'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
