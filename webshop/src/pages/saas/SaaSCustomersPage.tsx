import React, { useState } from 'react';
import { ColumnDef } from '@tanstack/react-table';
import { Users, UserPlus, Phone, Mail, Edit2, Trash2, X } from 'lucide-react';
import { DataTable } from '../../components/DataTable';
import { useToast } from '../../contexts/ToastContext';

interface CustomerItem {
  id: number;
  code: string;
  name: string;
  phone: string;
  email: string;
  taxCode: string;
  type: 'Khách sỉ' | 'Khách lẻ' | 'Đại lý';
  creditLimit: number;
  currentDebt: number;
}

export const SaaSCustomersPage: React.FC = () => {
  const { addToast } = useToast();
  const [customers, setCustomers] = useState<CustomerItem[]>([
    {
      id: 1,
      code: 'KH001',
      name: 'Công ty TNHH Giải Pháp Công Nghệ Việt',
      phone: '0901234567',
      email: 'contact@techviet.vn',
      taxCode: '0101234567',
      type: 'Khách sỉ',
      creditLimit: 200000000,
      currentDebt: 45000000,
    },
    {
      id: 2,
      code: 'KH002',
      name: 'Nguyễn Văn Minh (Cửa hàng Tin Học)',
      phone: '0912345678',
      email: 'minh.tinhoc@gmail.com',
      taxCode: '0109876543',
      type: 'Đại lý',
      creditLimit: 100000000,
      currentDebt: 12500000,
    },
    {
      id: 3,
      code: 'KH003',
      name: 'Trần Thị Thu Hà',
      phone: '0988776655',
      email: 'ha.tran@yahoo.com',
      taxCode: '-',
      type: 'Khách lẻ',
      creditLimit: 10000000,
      currentDebt: 0,
    },
  ]);

  const [showModal, setShowModal] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState<CustomerItem | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    taxCode: '',
    type: 'Khách sỉ' as 'Khách sỉ' | 'Khách lẻ' | 'Đại lý',
    creditLimit: 50000000,
  });

  const handleOpenAdd = () => {
    setEditingCustomer(null);
    setFormData({
      name: '',
      phone: '',
      email: '',
      taxCode: '',
      type: 'Khách sỉ',
      creditLimit: 50000000,
    });
    setShowModal(true);
  };

  const handleOpenEdit = (customer: CustomerItem) => {
    setEditingCustomer(customer);
    setFormData({
      name: customer.name,
      phone: customer.phone,
      email: customer.email,
      taxCode: customer.taxCode === '-' ? '' : customer.taxCode,
      type: customer.type,
      creditLimit: customer.creditLimit,
    });
    setShowModal(true);
  };

  const handleSave = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name) return;

    if (editingCustomer) {
      setCustomers(
        customers.map((c) =>
          c.id === editingCustomer.id
            ? {
                ...c,
                name: formData.name,
                phone: formData.phone,
                email: formData.email,
                taxCode: formData.taxCode || '-',
                type: formData.type,
                creditLimit: Number(formData.creditLimit),
              }
            : c
        )
      );
      addToast('Cập nhật hồ sơ khách hàng thành công!', 'success');
    } else {
      const newCust: CustomerItem = {
        id: Date.now(),
        code: `KH00${customers.length + 1}`,
        name: formData.name,
        phone: formData.phone,
        email: formData.email,
        taxCode: formData.taxCode || '-',
        type: formData.type,
        creditLimit: Number(formData.creditLimit),
        currentDebt: 0,
      };
      setCustomers([newCust, ...customers]);
      addToast('Thêm hồ sơ khách hàng mới thành công!', 'success');
    }
    setShowModal(false);
  };

  const handleDelete = (id: number, name: string) => {
    if (window.confirm(`Bạn có chắc chắn muốn xóa khách hàng "${name}"?`)) {
      setCustomers(customers.filter((c) => c.id !== id));
      addToast(`Đã xóa khách hàng "${name}"`, 'warning');
    }
  };

  const columns: ColumnDef<CustomerItem>[] = [
    {
      accessorKey: 'code',
      header: 'Mã KH',
      cell: (info) => (
        <span className="font-mono text-xs font-bold text-amber-600 dark:text-amber-400">
          {info.getValue() as string}
        </span>
      ),
    },
    {
      accessorKey: 'name',
      header: 'Tên Khách Hàng',
      cell: (info) => <span className="font-bold text-zinc-900 dark:text-zinc-100">{info.getValue() as string}</span>,
    },
    {
      accessorKey: 'phone',
      header: 'Liên Hệ',
      cell: (info) => (
        <div className="text-xs space-y-0.5">
          <div className="flex items-center gap-1 text-zinc-800 dark:text-zinc-200 font-medium">
            <Phone className="h-3 w-3 text-zinc-400" />
            {info.getValue() as string}
          </div>
          <div className="flex items-center gap-1 text-zinc-500">
            <Mail className="h-3 w-3 text-zinc-400" />
            {info.row.original.email}
          </div>
        </div>
      ),
    },
    {
      accessorKey: 'type',
      header: 'Phân Loại',
      cell: (info) => (
        <span className="px-2.5 py-0.5 rounded-full text-xs font-semibold bg-amber-100 dark:bg-amber-950/60 text-amber-700 dark:text-amber-300 border border-amber-200 dark:border-amber-800">
          {info.getValue() as string}
        </span>
      ),
    },
    {
      accessorKey: 'taxCode',
      header: 'Mã Số Thuế',
      cell: (info) => <span className="font-mono text-xs text-zinc-600 dark:text-zinc-400">{info.getValue() as string}</span>,
    },
    {
      accessorKey: 'currentDebt',
      header: 'Nợ Phải Thu',
      cell: (info) => {
        const debt = info.getValue() as number;
        return (
          <span className={`font-bold ${debt > 0 ? 'text-amber-600 dark:text-amber-400' : 'text-zinc-500'}`}>
            {debt.toLocaleString('vi-VN')} đ
          </span>
        );
      },
    },
    {
      accessorKey: 'creditLimit',
      header: 'Hạn Mức Nợ',
      cell: (info) => `${(info.getValue() as number).toLocaleString('vi-VN')} đ`,
    },
    {
      id: 'actions',
      header: 'Thao Tác',
      cell: ({ row }) => (
        <div className="flex items-center gap-1">
          <button
            onClick={() => handleOpenEdit(row.original)}
            className="p-1.5 rounded-md hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-600 dark:text-zinc-300 transition-colors"
            title="Chỉnh sửa thông tin"
          >
            <Edit2 className="h-4 w-4 text-amber-500" />
          </button>
          <button
            onClick={() => handleDelete(row.original.id, row.original.name)}
            className="p-1.5 rounded-md hover:bg-red-50 dark:hover:bg-red-950/40 text-red-600 dark:text-red-400 transition-colors"
            title="Xóa khách hàng"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
            <Users className="h-6 w-6 text-amber-500" /> Hồ Sơ Khách Hàng
          </h2>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Quản lý danh sách khách hàng, mã số thuế, hạn mức công nợ và lịch sử giao dịch.
          </p>
        </div>
        <button
          onClick={handleOpenAdd}
          className="inline-flex items-center gap-2 px-4 py-2 text-xs font-bold rounded-lg bg-amber-500 hover:bg-amber-600 text-zinc-950 shadow-xs transition-all"
        >
          <UserPlus className="h-4 w-4" /> Thêm khách hàng
        </button>
      </div>

      <DataTable columns={columns} data={customers} searchPlaceholder="Tìm tên khách hàng, SĐT, mã số thuế..." />

      {showModal && (
        <div className="fixed inset-0 z-50 bg-zinc-950/60 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white dark:bg-zinc-900 rounded-2xl max-w-lg w-full p-6 border border-zinc-200 dark:border-zinc-800 shadow-2xl space-y-5">
            <div className="flex items-center justify-between border-b border-zinc-100 dark:border-zinc-800 pb-3">
              <h3 className="text-base font-bold text-zinc-900 dark:text-zinc-100 flex items-center gap-2">
                <Users className="h-5 w-5 text-amber-500" />
                {editingCustomer ? 'Chỉnh Sửa Hồ Sơ Khách Hàng' : 'Thêm Hồ Sơ Khách Hàng Mới'}
              </h3>
              <button
                onClick={() => setShowModal(false)}
                className="p-1 rounded-lg hover:bg-zinc-100 dark:hover:bg-zinc-800 text-zinc-400"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            <form onSubmit={handleSave} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">Tên Khách Hàng / Công ty *</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  placeholder="Nhập tên khách hàng"
                  className="w-full px-3 py-2 text-sm font-semibold bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">Phân Loại Khách Hàng</label>
                  <select
                    value={formData.type}
                    onChange={(e) => setFormData({ ...formData, type: e.target.value as any })}
                    className="w-full px-3 py-2 text-sm font-semibold bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                  >
                    <option value="Khách sỉ">Khách sỉ</option>
                    <option value="Khách lẻ">Khách lẻ</option>
                    <option value="Đại lý">Đại lý</option>
                  </select>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">Số điện thoại</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">Email</label>
                  <input
                    type="email"
                    value={formData.email}
                    onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                    className="w-full px-3 py-2 text-sm bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">Mã Số Thuế</label>
                  <input
                    type="text"
                    value={formData.taxCode}
                    onChange={(e) => setFormData({ ...formData, taxCode: e.target.value })}
                    className="w-full px-3 py-2 text-sm font-mono bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-zinc-700 dark:text-zinc-300 mb-1">Hạn Mức Cho Nợ (VND)</label>
                <input
                  type="number"
                  value={formData.creditLimit}
                  onChange={(e) => setFormData({ ...formData, creditLimit: Number(e.target.value) })}
                  className="w-full px-3 py-2 text-sm font-mono font-bold bg-zinc-50 dark:bg-zinc-800 border border-zinc-200 dark:border-zinc-700 rounded-lg text-zinc-900 dark:text-zinc-100"
                />
              </div>

              <div className="flex items-center justify-end gap-3 pt-3 border-t border-zinc-200 dark:border-zinc-800">
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="px-4 py-2 text-xs font-semibold text-zinc-600 dark:text-zinc-400 hover:bg-zinc-100 dark:hover:bg-zinc-800 rounded-lg"
                >
                  Hủy Bỏ
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-xs font-bold text-zinc-950 bg-amber-500 hover:bg-amber-600 rounded-lg shadow-xs"
                >
                  {editingCustomer ? 'Cập Nhật Khách Hàng' : 'Lưu Khách Hàng'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
