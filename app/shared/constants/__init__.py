class DocStatus:
    DRAFT = "draft"
    CONFIRMED = "confirmed"
    CANCELLED = "cancelled"

    ALL = {DRAFT, CONFIRMED, CANCELLED}


class DebtStatus:
    OPEN = "open"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"

    ACTIVE = {OPEN, PARTIAL, OVERDUE}


class Roles:
    """Tập vai trò hệ thống tập trung (single source of truth)."""

    ADMIN = "admin"
    ACCOUNTANT = "accountant"
    WAREHOUSE = "warehouse"
    USER = "user"
    WEB_CUSTOMER = "web_customer"
    ERP_USER = "erp_user"

    ALL = {ADMIN, ACCOUNTANT, WAREHOUSE, USER, WEB_CUSTOMER, ERP_USER}
    # Vai trò nội bộ (nhân viên) dùng cho phân quyền ERP
    INTERNAL = {ADMIN, ACCOUNTANT, WAREHOUSE, USER}

    @classmethod
    def is_valid(cls, role: str) -> bool:
        return (role or "").strip().lower() in cls.ALL

    @classmethod
    def normalize(cls, role: str) -> str:
        return (role or USER).strip().lower()
