from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import text

from app.database import db


def _as_date(value, fallback=None):
    if isinstance(value, date):
        return value
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, str) and value:
        return datetime.strptime(value, "%Y-%m-%d").date()
    return fallback or date.today()


class TT99ReportService:
    @staticmethod
    def get_balance_sheet(as_of_date):
        as_of = _as_date(as_of_date)
        sql = text(
            """
            SELECT
                ac.code,
                ac.name,
                ac.account_type,
                ac.normal_balance,
                ac.level,
                ac.parent_id,
                COALESCE(
                    CASE
                        WHEN ac.normal_balance = 'debit' THEN
                            SUM(CASE WHEN je.id IS NOT NULL THEN jl.debit ELSE 0 END) -
                            SUM(CASE WHEN je.id IS NOT NULL THEN jl.credit ELSE 0 END)
                        ELSE
                            SUM(CASE WHEN je.id IS NOT NULL THEN jl.credit ELSE 0 END) -
                            SUM(CASE WHEN je.id IS NOT NULL THEN jl.debit ELSE 0 END)
                    END
                , 0) AS balance
            FROM account_charts ac
            LEFT JOIN journal_lines jl ON jl.account_id = ac.id
            LEFT JOIN journal_entries je
                   ON je.id = jl.entry_id
                  AND je.status = 'posted'
                  AND je.date <= :as_of
            WHERE ac.is_active = TRUE
            GROUP BY ac.code, ac.name, ac.account_type, ac.normal_balance, ac.level, ac.parent_id
            ORDER BY ac.code
            """
        )
        result = db.session.execute(sql, {"as_of": as_of})
        return [dict(row._mapping) for row in result]

    @staticmethod
    def get_income_statement(start_date, end_date):
        start = _as_date(start_date)
        end = _as_date(end_date)
        sql = text(
            """
            SELECT
                ac.code,
                ac.name,
                ac.account_type,
                ac.normal_balance,
                COALESCE(SUM(CASE WHEN je.id IS NOT NULL THEN jl.debit ELSE 0 END), 0) AS total_debit,
                COALESCE(SUM(CASE WHEN je.id IS NOT NULL THEN jl.credit ELSE 0 END), 0) AS total_credit,
                CASE
                    WHEN ac.normal_balance = 'debit' THEN
                        COALESCE(SUM(CASE WHEN je.id IS NOT NULL THEN jl.debit ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN je.id IS NOT NULL THEN jl.credit ELSE 0 END), 0)
                    ELSE
                        COALESCE(SUM(CASE WHEN je.id IS NOT NULL THEN jl.credit ELSE 0 END), 0) -
                        COALESCE(SUM(CASE WHEN je.id IS NOT NULL THEN jl.debit ELSE 0 END), 0)
                END AS net_amount
            FROM account_charts ac
            LEFT JOIN journal_lines jl ON jl.account_id = ac.id
            LEFT JOIN journal_entries je
                   ON je.id = jl.entry_id
                  AND je.status = 'posted'
                  AND je.date BETWEEN :start AND :end
            WHERE ac.is_active = TRUE
              AND ac.account_type IN ('revenue', 'cogs', 'expense', 'other_income', 'other_expense')
            GROUP BY ac.code, ac.name, ac.account_type, ac.normal_balance
            ORDER BY ac.code
            """
        )
        result = db.session.execute(sql, {"start": start, "end": end})
        return [dict(row._mapping) for row in result]

    @staticmethod
    def get_trial_balance(start_date, end_date):
        start = _as_date(start_date)
        end = _as_date(end_date)

        sql = text(
            """
            WITH opening AS (
                SELECT
                    ac.id AS account_id,
                    ac.code AS account_code,
                    ac.name AS account_name,
                    ac.account_type,
                    ac.normal_balance,
                    COALESCE(
                        CASE
                            WHEN ac.normal_balance = 'debit' THEN SUM(jl.debit - jl.credit)
                            ELSE SUM(jl.credit - jl.debit)
                        END
                    , 0) AS opening_balance
                FROM account_charts ac
                LEFT JOIN journal_lines jl ON jl.account_id = ac.id
                LEFT JOIN journal_entries je
                       ON je.id = jl.entry_id
                      AND je.status = 'posted'
                      AND je.date < :start
                WHERE ac.is_active = TRUE
                  AND ac.is_detail = TRUE
                GROUP BY ac.id, ac.code, ac.name, ac.account_type, ac.normal_balance
            ),
            movements AS (
                SELECT
                    jl.account_id,
                    COALESCE(SUM(jl.debit), 0) AS period_debit,
                    COALESCE(SUM(jl.credit), 0) AS period_credit
                FROM journal_lines jl
                JOIN journal_entries je ON je.id = jl.entry_id
                WHERE je.status = 'posted'
                  AND je.date BETWEEN :start AND :end
                GROUP BY jl.account_id
            )
            SELECT
                o.account_id,
                o.account_code,
                o.account_name,
                o.account_type,
                o.normal_balance,
                o.opening_balance,
                COALESCE(m.period_debit, 0) AS period_debit,
                COALESCE(m.period_credit, 0) AS period_credit,
                CASE
                    WHEN o.normal_balance = 'debit' THEN o.opening_balance + COALESCE(m.period_debit, 0) - COALESCE(m.period_credit, 0)
                    ELSE o.opening_balance + COALESCE(m.period_credit, 0) - COALESCE(m.period_debit, 0)
                END AS closing_balance
            FROM opening o
            LEFT JOIN movements m ON m.account_id = o.account_id
            ORDER BY o.account_code
            """
        )
        rows = db.session.execute(sql, {"start": start, "end": end}).mappings().all()

        results = []
        for row in rows:
            opening = Decimal(str(row["opening_balance"] or 0))
            period_debit = Decimal(str(row["period_debit"] or 0))
            period_credit = Decimal(str(row["period_credit"] or 0))
            closing = Decimal(str(row["closing_balance"] or 0))
            normal = row["normal_balance"] or "debit"

            if normal == "debit":
                opening_debit = opening if opening > 0 else Decimal("0")
                opening_credit = abs(opening) if opening < 0 else Decimal("0")
                closing_debit = closing if closing > 0 else Decimal("0")
                closing_credit = abs(closing) if closing < 0 else Decimal("0")
            else:
                opening_debit = abs(opening) if opening < 0 else Decimal("0")
                opening_credit = opening if opening > 0 else Decimal("0")
                closing_debit = abs(closing) if closing < 0 else Decimal("0")
                closing_credit = closing if closing > 0 else Decimal("0")

            results.append({
                "account_id": row["account_id"],
                "account_code": row["account_code"],
                "account_name": row["account_name"],
                "account_type": row["account_type"],
                "opening_debit": float(opening_debit),
                "opening_credit": float(opening_credit),
                "period_debit": float(period_debit),
                "period_credit": float(period_credit),
                "closing_debit": float(closing_debit),
                "closing_credit": float(closing_credit),
                "has_movement": bool(period_debit > 0 or period_credit > 0 or opening_debit > 0 or opening_credit > 0),
            })

        return results

    @staticmethod
    def get_general_ledger(account_code, start_date, end_date):
        start = _as_date(start_date)
        end = _as_date(end_date)

        opening_sql = text(
            """
            SELECT
                ac.normal_balance AS normal_balance,
                COALESCE(
                    CASE
                        WHEN ac.normal_balance = 'debit' THEN SUM(jl.debit - jl.credit)
                        ELSE SUM(jl.credit - jl.debit)
                    END
                , 0) AS opening_balance
            FROM account_charts ac
            LEFT JOIN journal_lines jl ON jl.account_id = ac.id
            LEFT JOIN journal_entries je
                   ON je.id = jl.entry_id
                  AND je.status = 'posted'
                  AND je.date < :start
            WHERE ac.code = :account_code
            GROUP BY ac.normal_balance
            """
        )
        opening_row = db.session.execute(
            opening_sql, {"account_code": account_code, "start": start}
        ).mappings().first()

        normal_balance = (opening_row["normal_balance"] if opening_row else "debit") or "debit"
        opening_balance = Decimal(str(opening_row["opening_balance"])) if opening_row else Decimal("0")

        movements_sql = text(
            """
            SELECT
                je.date,
                je.code AS entry_code,
                COALESCE(jl.description, je.description, '') AS description,
                COALESCE(jl.debit, 0) AS debit,
                COALESCE(jl.credit, 0) AS credit
            FROM journal_lines jl
            JOIN journal_entries je ON je.id = jl.entry_id
            JOIN account_charts ac ON ac.id = jl.account_id
            WHERE ac.code = :account_code
              AND je.status = 'posted'
              AND je.date BETWEEN :start AND :end
            ORDER BY je.date, je.id, jl.order_no, jl.id
            """
        )
        rows = db.session.execute(
            movements_sql, {"account_code": account_code, "start": start, "end": end}
        ).mappings().all()

        running = opening_balance
        results = []
        for row in rows:
            debit = Decimal(str(row["debit"] or 0))
            credit = Decimal(str(row["credit"] or 0))
            if normal_balance == "debit":
                running = running + debit - credit
                run_db = running if running > 0 else Decimal("0")
                run_cr = abs(running) if running < 0 else Decimal("0")
            else:
                running = running + credit - debit
                run_db = abs(running) if running < 0 else Decimal("0")
                run_cr = running if running > 0 else Decimal("0")

            results.append(
                {
                    "date": row["date"],
                    "entry_code": row["entry_code"],
                    "description": row["description"],
                    "debit": float(debit),
                    "credit": float(credit),
                    "running_debit_balance": float(run_db),
                    "running_credit_balance": float(run_cr),
                }
            )

        if normal_balance == "debit":
            opening_debit = opening_balance if opening_balance > 0 else 0
            opening_credit = abs(opening_balance) if opening_balance < 0 else 0
            closing_debit = running if running > 0 else 0
            closing_credit = abs(running) if running < 0 else 0
        else:
            opening_debit = abs(opening_balance) if opening_balance < 0 else 0
            opening_credit = opening_balance if opening_balance > 0 else 0
            closing_debit = abs(running) if running < 0 else 0
            closing_credit = running if running > 0 else 0

        return {
            "lines": results,
            "normal_balance": normal_balance,
            "opening_balance": float(opening_balance),
            "closing_balance": float(running),
            "opening_debit": float(opening_debit),
            "opening_credit": float(opening_credit),
            "closing_debit": float(closing_debit),
            "closing_credit": float(closing_credit),
        }

    @staticmethod
    def get_detail_ledger(account_code, start_date, end_date, partner_id=None):
        start = _as_date(start_date)
        end = _as_date(end_date)

        params = {"account_code": account_code, "start": start, "end": end}
        partner_filter = ""
        if partner_id:
            params["partner_id"] = partner_id
            partner_filter = " AND jl.partner_id = :partner_id "

        sql = text(
            f"""
            WITH opening AS (
                SELECT
                    ac.normal_balance,
                    jl.partner_id,
                    COALESCE(
                        CASE
                            WHEN ac.normal_balance = 'debit' THEN SUM(jl.debit - jl.credit)
                            ELSE SUM(jl.credit - jl.debit)
                        END
                    , 0) AS opening_balance
                FROM journal_lines jl
                JOIN journal_entries je ON je.id = jl.entry_id
                JOIN account_charts ac ON ac.id = jl.account_id
                WHERE ac.code = :account_code
                  AND je.status = 'posted'
                  AND je.date < :start
                  {partner_filter}
                GROUP BY ac.normal_balance, jl.partner_id
            ),
            movements AS (
                SELECT
                    je.date,
                    je.code AS entry_code,
                    COALESCE(jl.description, je.description, '') AS description,
                    COALESCE(jl.debit, 0) AS debit,
                    COALESCE(jl.credit, 0) AS credit,
                    jl.partner_id,
                    ac.normal_balance,
                    CASE
                        WHEN :account_code = '131' THEN c.name
                        WHEN :account_code = '331' THEN s.name
                        ELSE COALESCE(jl.description, je.reference_code, je.code, 'Khác')
                    END AS partner_name
                FROM journal_lines jl
                JOIN journal_entries je ON je.id = jl.entry_id
                JOIN account_charts ac ON ac.id = jl.account_id
                LEFT JOIN customers c ON c.id = jl.partner_id
                LEFT JOIN suppliers s ON s.id = jl.partner_id
                WHERE ac.code = :account_code
                  AND je.status = 'posted'
                  AND je.date BETWEEN :start AND :end
                  {partner_filter}
            )
            SELECT
                m.partner_id,
                COALESCE(m.partner_name, 'Chưa phân nhóm') AS partner_name,
                m.date,
                m.entry_code,
                m.description,
                m.debit,
                m.credit,
                m.normal_balance,
                COALESCE(o.opening_balance, 0) AS opening_balance
            FROM movements m
            LEFT JOIN opening o
                   ON o.partner_id IS NOT DISTINCT FROM m.partner_id
            ORDER BY COALESCE(m.partner_name, 'Chưa phân nhóm'), m.date, m.entry_code
            """
        )

        rows = db.session.execute(sql, params).mappings().all()
        running_map = {}
        out = []
        for row in rows:
            partner_key = row["partner_id"]
            if partner_key not in running_map:
                running_map[partner_key] = Decimal(str(row["opening_balance"] or 0))

            debit = Decimal(str(row["debit"] or 0))
            credit = Decimal(str(row["credit"] or 0))
            normal = row["normal_balance"] or "debit"
            if normal == "debit":
                running_map[partner_key] = running_map[partner_key] + debit - credit
                run_db = running_map[partner_key] if running_map[partner_key] > 0 else Decimal("0")
                run_cr = abs(running_map[partner_key]) if running_map[partner_key] < 0 else Decimal("0")
            else:
                running_map[partner_key] = running_map[partner_key] + credit - debit
                run_db = abs(running_map[partner_key]) if running_map[partner_key] < 0 else Decimal("0")
                run_cr = running_map[partner_key] if running_map[partner_key] > 0 else Decimal("0")

            out.append(
                {
                    "partner_id": row["partner_id"],
                    "partner_name": row["partner_name"],
                    "date": row["date"],
                    "entry_code": row["entry_code"],
                    "description": row["description"],
                    "debit": float(debit),
                    "credit": float(credit),
                    "running_debit_balance": float(run_db),
                    "running_credit_balance": float(run_cr),
                }
            )

        return out
