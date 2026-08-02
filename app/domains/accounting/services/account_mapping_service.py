from app.database import db
from app.domains.platform.models import SystemConfig


ACCOUNT_MAPPING_DEFAULTS = {
    "acc_cash": "111",
    "acc_bank": "112",
    "acc_ar": "131",
    "acc_ap": "331",
    "acc_inventory": "1561",
    "acc_vat_in": "1331",
    "acc_vat_out": "3331",
    "acc_revenue": "511",
    "acc_cogs": "632",
}


def get_account_code(key: str) -> str:
    cfg = SystemConfig.query.filter_by(key=key).first()
    value = (cfg.value.strip() if cfg and cfg.value else "")
    if value:
        return value
    return ACCOUNT_MAPPING_DEFAULTS.get(key, "")


def ensure_account_mapping_configs():
    for key, default_code in ACCOUNT_MAPPING_DEFAULTS.items():
        exists = SystemConfig.query.filter_by(key=key).first()
        if exists:
            continue
        db.session.add(SystemConfig(
            key=key,
            value=default_code,
            description=f"Account mapping: {key}",
            group_name="accounting",
        ))
    db.session.commit()
