import React, { useState } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { Boxes, PackageCheck, AlertTriangle } from 'lucide-react';
import { DataTable } from '../../components/DataTable';

interface InventoryItem {
  id: number;
  sku: string;
  name: string;
  warehouse: string;
  stock: number;
  reserved: number;
  available: number;
  unitCost: number;
  totalValue: number;
}

export const SaaSInventoryPage: React.FC = () => {
  const [items] = useState<InventoryItem[]>([
    {
      id: 1,
      sku: 'SP001',
      name: 'Laptop Dell Inspiron 15 3520',
      warehouse: 'Kho Chính - Hà Nội',
      stock: 15,
      reserved: 2,
      available: 13,
      unitCost: 15500000,
      totalValue: 232500000,
    },
    {
      id: 2,
      sku: 'SP002',
      name: 'Chuột không dây Logitech M235',
      warehouse: 'Kho Chính - Hà Nội',
      stock: 45,
      reserved: 5,
      available: 40,
      unitCost: 240000,
      totalValue: 10800000,
    },
    {
      id: 3,
      sku: 'VT001',
      name: 'Giấy A4 Double A 70gsm (Ream 500 tờ)',
      warehouse: 'Kho Phụ - HCM',
      stock: 120,
      reserved: 10,
      available: 110,
      unitCost: 52000,
      totalValue: 6240000,
    },
  ]);

  const columns: ColumnDef<InventoryItem>[] = [
    {
      accessorKey: 'sku',
      header: 'Mã SKU',
      cell: (info) => (
        <span className="font-mono text-xs font-bold text-amber-600 dark:text-amber-400">
          {info.getValue() as string}
        </span>
      ),
    },
    {
      accessorKey: 'name',
      header: 'Tên Hàng Hóa',
      cell: (info) => <span className="font-semibold text-zinc-900 dark:text-zinc-100">{info.getValue() as string}</span>,
    },
    {
      accessorKey: 'warehouse',
      header: 'Kho Hàng',
    },
    {
      accessorKey: 'stock',
      header: 'Tồn Kho Thực Tế',
      cell: (info) => <span className="font-bold text-zinc-900 dark:text-zinc-100">{info.getValue() as number}</span>,
    },
    {
      accessorKey: 'available',
      header: 'Khả Dụng Bán',
      cell: (info) => <span className="font-bold text-emerald-600 dark:text-emerald-400">{info.getValue() as number}</span>,
    },
    {
      accessorKey: 'unitCost',
      header: 'Giá Vốn Bình Quân',
      cell: (info) => `${(info.getValue() as number).toLocaleString('vi-VN')} đ`,
    },
    {
      accessorKey: 'totalValue',
      header: 'Tổng Giá Trị Tồn Kho',
      cell: (info) => (
        <span className="font-bold text-amber-600 dark:text-amber-400">
          {(info.getValue() as number).toLocaleString('vi-VN')} đ
        </span>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Boxes className="h-6 w-6 text-amber-500" /> Báo Cáo Kiểm Kê & Định Giá Tồn Kho
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Số liệu tổng hợp tồn kho thực tế, tồn kho tạm giữ và tổng giá trị tài sản lưu kho theo phương pháp bình quân.
          </p>
        </div>
      </div>

      <DataTable columns={columns} data={items} searchPlaceholder="Tìm mã SKU, tên hàng hóa..." />
    </div>
  );
};
