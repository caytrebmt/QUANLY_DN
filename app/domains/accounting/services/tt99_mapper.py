from decimal import Decimal

class TT99Mapper:
    BALANCE_SHEET_MAP = {
        "A.I.1": {"label": "Tien va cac khoan tuong duong tien", "accounts": ["111", "112", "113"]},
        "A.I.2": {"label": "Dau tu tai chinh ngan han", "accounts": ["121", "128"]},
        "A.I.3": {"label": "Cac khoan phai thu ngan han", "accounts": ["131", "136", "138", "141"]},
        "A.I.4": {"label": "Hang ton kho", "accounts": ["151", "152", "153", "154", "155", "156", "157"]},
        "A.I.5": {"label": "Tai san ngan han khac", "accounts": ["161", "242"]},
        "A.II.1": {"label": "Tai san co dinh", "accounts": ["211", "212", "213"], "contra": ["214"]},
        "A.II.2": {"label": "Bat dong san dau tu", "accounts": ["22"]},
        "A.II.3": {"label": "Dau tu tai chinh dai han", "accounts": ["228"]},
        "B.I.1": {"label": "Vay va no thue tai chinh ngan han", "accounts": ["311"]},
        "B.I.2": {"label": "Phai tra nguoi ban", "accounts": ["331"]},
        "B.I.3": {"label": "Thue va cac khoan phai nop NN", "accounts": ["333"]},
        "B.I.4": {"label": "Phai tra nguoi lao dong", "accounts": ["334"]},
        "B.I.5": {"label": "Chi phi phai tra", "accounts": ["335"]},
        "B.I.6": {"label": "Vay va no thue tai chinh dai han", "accounts": ["341"]},
        "C.I.1": {"label": "Von dau tu cua chu so huu", "accounts": ["411"]},
        "C.I.2": {"label": "Loi nhuan sau thue chua phan phoi", "accounts": ["421"]},
        "C.I.3": {"label": "Cac quy khac", "accounts": ["412", "413", "414", "417", "418"]},
    }
    INCOME_STATEMENT_MAP = {
        "01": {"label": "Doanh thu ban hang va CCDV", "accounts": ["511", "512"], "sign": 1},
        "02": {"label": "Cac khoan giam tru doanh thu", "accounts": ["521"], "sign": -1},
        "10": {"label": "Doanh thu thuan", "formula": "01+02"},
        "11": {"label": "Gia von hang ban", "accounts": ["632"], "sign": -1},
        "20": {"label": "Loi nhuan gop", "formula": "10+11"},
        "21": {"label": "Doanh thu hoat dong tai chinh", "accounts": ["515"], "sign": 1},
        "22": {"label": "Chi phi tai chinh", "accounts": ["635"], "sign": -1},
        "24": {"label": "Chi phi ban hang", "accounts": ["641"], "sign": -1},
        "25": {"label": "Chi phi QLDN", "accounts": ["642"], "sign": -1},
        "30": {"label": "Loi nhuan thuan tu HĐKD", "formula": "20+21+22+24+25"},
        "31": {"label": "Thu nhap khac", "accounts": ["711"], "sign": 1},
        "32": {"label": "Chi phi khac", "accounts": ["811"], "sign": -1},
        "40": {"label": "Loi nhuan khac", "formula": "31+32"},
        "50": {"label": "Loi nhuan truoc thue", "formula": "30+40"},
        "51": {"label": "Chi phi thue TNDN", "accounts": ["821"], "sign": -1},
        "60": {"label": "Loi nhuan sau thue", "formula": "50+51"},
    }

    @classmethod
    def map_balance_sheet(cls, raw_data: list) -> dict:
        balance_map = {row["code"]: Decimal(str(row["balance"])) for row in raw_data}
        result = {}
        for line_code, cfg in cls.BALANCE_SHEET_MAP.items():
            total = Decimal(0)
            for acc in cfg.get("accounts", []):
                total += balance_map.get(acc, Decimal(0)) * cfg.get("sign", 1)
            for contra in cfg.get("contra", []):
                total -= balance_map.get(contra, Decimal(0))
            result[line_code] = {
                "label": cfg["label"],
                "amount": float(abs(total.quantize(Decimal("0.01"))))
            }
        return result

    @classmethod
    def map_income_statement(cls, raw_data: list) -> list:
        amount_map = {row["code"]: Decimal(str(row["net_amount"])) for row in raw_data}
        result = []
        calculated = {}
        for line_code, cfg in cls.INCOME_STATEMENT_MAP.items():
            if "accounts" in cfg:
                val = sum(
                    amount_map.get(acc, Decimal(0)) * cfg.get("sign", 1)
                    for acc in cfg["accounts"]
                )
            elif "formula" in cfg:
                parts = cfg["formula"].replace("-", "+-").split("+")
                val = sum(
                    calculated.get(p.lstrip('-'), Decimal(0)) * (-1 if p.startswith('-') else 1)
                    for p in parts
                )
            else:
                val = Decimal(0)
            display_val = abs(val)
            calculated[line_code] = val
            result.append({
                "ma_so": line_code,
                "chi_tieu": cfg["label"],
                "so_tien": float(display_val.quantize(Decimal("0.01")))
            })
        return result
