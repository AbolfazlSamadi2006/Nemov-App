import jdatetime
from datetime import datetime
from sqlalchemy import or_, and_, func
from nemov.database.connection import get_session, mark_data_changed
from nemov.models.database_models import ClubExpense, TuitionPayment, Member, User
from nemov.utils.jalali_date import (
    get_today_shamsi, parse_shamsi, format_shamsi, is_valid_shamsi
)
from nemov.utils.logger import log_info, log_error

EXPENSE_CATEGORIES = [
    "قبوض (آب، برق، گاز)",
    "اجاره و شارژ مجموعه",
    "تعمیر و نگهداری تجهیزات",
    "اقلام بهداشتی و نظافت",
    "خرید تجهیزات ورزشی",
    "خرید بوفه و مکمل",
    "دستمزد و حقوق پرسنل",
    "تبلیغات و بازاریابی",
    "نرم‌افزار و اینترنت",
    "متفرقه"
]

class AccountingService:
    @staticmethod
    def get_date_range_for_filter(filter_key: str):
        """
        Returns (start_date_shamsi, end_date_shamsi) formatted as YYYY/MM/DD.
        filter_key: 'today', 'this_week', 'this_month', 'this_year', 'last_30_days', 'all'
        """
        today = jdatetime.date.today()
        today_str = today.strftime("%Y/%m/%d")

        if filter_key == "today":
            return today_str, today_str

        elif filter_key == "this_week":
            # In Iran / jdatetime: Saturday=0, Friday=6
            start_week = today - jdatetime.timedelta(days=today.weekday())
            end_week = start_week + jdatetime.timedelta(days=6)
            return start_week.strftime("%Y/%m/%d"), end_week.strftime("%Y/%m/%d")

        elif filter_key == "this_month":
            start_month = jdatetime.date(today.year, today.month, 1)
            if today.month <= 6:
                end_day = 31
            elif today.month <= 11:
                end_day = 30
            else:
                end_day = 30 if today.isleap() else 29
            end_month = jdatetime.date(today.year, today.month, end_day)
            return start_month.strftime("%Y/%m/%d"), end_month.strftime("%Y/%m/%d")

        elif filter_key == "this_year":
            start_year = jdatetime.date(today.year, 1, 1)
            end_day = 30 if today.isleap() else 29
            end_year = jdatetime.date(today.year, 12, end_day)
            return start_year.strftime("%Y/%m/%d"), end_year.strftime("%Y/%m/%d")

        elif filter_key == "last_30_days":
            start_date = today - jdatetime.timedelta(days=30)
            return start_date.strftime("%Y/%m/%d"), today_str

        return None, None  # 'all'

    @staticmethod
    def get_all_trainers():
        """Returns list of active trainers for filtering and selection (excluding admin)."""
        session = get_session()
        try:
            return session.query(User).filter(
                User.role == "trainer",
                User.username != "admin",
                User.is_active == True
            ).order_by(User.id.asc()).all()
        finally:
            session.close()

    @staticmethod
    def get_financial_summary(start_date=None, end_date=None, user_id=None):
        """
        Calculates total income, total expense, and net profit for given date range and optional trainer.
        """
        session = get_session()
        try:
            # 1. Income query (Tuition payments)
            inc_query = session.query(
                func.coalesce(func.sum(TuitionPayment.amount), 0.0),
                func.count(TuitionPayment.id)
            )
            if user_id is not None and user_id > 0:
                inc_query = inc_query.filter(TuitionPayment.user_id == user_id)
            if start_date:
                inc_query = inc_query.filter(TuitionPayment.payment_date_shamsi >= start_date)
            if end_date:
                inc_query = inc_query.filter(TuitionPayment.payment_date_shamsi <= end_date)
            
            total_income, income_count = inc_query.first() or (0.0, 0)

            # 2. Expense query (Club expenses)
            exp_query = session.query(
                func.coalesce(func.sum(ClubExpense.amount), 0.0),
                func.count(ClubExpense.id)
            )
            if user_id is not None and user_id > 0:
                exp_query = exp_query.filter(ClubExpense.user_id == user_id)
            if start_date:
                exp_query = exp_query.filter(ClubExpense.expense_date_shamsi >= start_date)
            if end_date:
                exp_query = exp_query.filter(ClubExpense.expense_date_shamsi <= end_date)

            total_expense, expense_count = exp_query.first() or (0.0, 0)

            total_income = float(total_income or 0.0)
            total_expense = float(total_expense or 0.0)
            net_profit = total_income - total_expense

            return {
                "total_income": total_income,
                "total_expense": total_expense,
                "net_profit": net_profit,
                "income_count": income_count,
                "expense_count": expense_count,
                "total_transactions": income_count + expense_count
            }
        finally:
            session.close()

    @staticmethod
    def get_transactions(start_date=None, end_date=None, user_id=None, transaction_type="all", search_query=None):
        """
        Returns unified list of transactions (income and expenses), sorted by date descending.
        """
        session = get_session()
        try:
            items = []

            # 1. Fetch Incomes if requested
            if transaction_type in ["all", "income"]:
                query = session.query(TuitionPayment).join(
                    Member, TuitionPayment.member_id == Member.id
                ).outerjoin(
                    User, TuitionPayment.user_id == User.id
                )

                if user_id is not None and user_id > 0:
                    query = query.filter(TuitionPayment.user_id == user_id)
                if start_date:
                    query = query.filter(TuitionPayment.payment_date_shamsi >= start_date)
                if end_date:
                    query = query.filter(TuitionPayment.payment_date_shamsi <= end_date)
                if search_query and search_query.strip():
                    pattern = f"%{search_query.strip()}%"
                    query = query.filter(
                        or_(
                            Member.first_name.like(pattern),
                            Member.last_name.like(pattern),
                            TuitionPayment.notes.like(pattern)
                        )
                    )

                incomes = query.order_by(TuitionPayment.payment_date_shamsi.desc(), TuitionPayment.id.desc()).all()
                for inc in incomes:
                    member_name = inc.member.full_name if inc.member else "ورزشکار نامشخص"
                    trainer_name = inc.trainer.display_name if inc.trainer else (inc.member.trainer.display_name if (inc.member and inc.member.trainer) else "باشگاه")
                    pay_type = inc.payment_type or "شهریه دوره ماهانه"
                    if pay_type in ["شهریه دوره", "تمدید عضویت باشگاه"]:
                        pay_type = "شهریه دوره ماهانه"
                    items.append({
                        "id": inc.id,
                        "type": "income",
                        "title": f"شهریه: {member_name}",
                        "party": member_name,
                        "category": pay_type,
                        "amount": float(inc.amount),
                        "date_shamsi": inc.payment_date_shamsi,
                        "user_id": inc.user_id,
                        "trainer_name": trainer_name,
                        "description": inc.notes or "-",
                        "member_id": inc.member_id
                    })

            # 2. Fetch Expenses if requested
            if transaction_type in ["all", "expense"]:
                query = session.query(ClubExpense).outerjoin(
                    User, ClubExpense.user_id == User.id
                )

                if user_id is not None and user_id > 0:
                    query = query.filter(ClubExpense.user_id == user_id)
                if start_date:
                    query = query.filter(ClubExpense.expense_date_shamsi >= start_date)
                if end_date:
                    query = query.filter(ClubExpense.expense_date_shamsi <= end_date)
                if search_query and search_query.strip():
                    pattern = f"%{search_query.strip()}%"
                    query = query.filter(
                        or_(
                            ClubExpense.title.like(pattern),
                            ClubExpense.category.like(pattern),
                            ClubExpense.description.like(pattern)
                        )
                    )

                expenses = query.order_by(ClubExpense.expense_date_shamsi.desc(), ClubExpense.id.desc()).all()
                for exp in expenses:
                    trainer_name = exp.user.display_name if exp.user else "مدیر باشگاه"
                    items.append({
                        "id": exp.id,
                        "type": "expense",
                        "title": exp.title,
                        "party": exp.title,
                        "category": exp.category or "متفرقه",
                        "amount": float(exp.amount),
                        "date_shamsi": exp.expense_date_shamsi,
                        "user_id": exp.user_id,
                        "trainer_name": trainer_name,
                        "description": exp.description or "-",
                        "member_id": None
                    })

            # Sort combined transactions by Shamsi date descending
            items.sort(key=lambda x: (x["date_shamsi"], x["id"]), reverse=True)
            return items
        finally:
            session.close()

    @staticmethod
    def add_expense(title: str, amount: float, expense_date_shamsi: str, category: str = "متفرقه", description: str = "", user_id: int = None) -> ClubExpense:
        """Adds a new club expense."""
        if not title or not title.strip():
            raise ValueError("عنوان هزینه نمی‌تواند خالی باشد.")
        if amount <= 0:
            raise ValueError("مبلغ هزینه باید بیشتر از صفر باشد.")
        if not is_valid_shamsi(expense_date_shamsi):
            raise ValueError("تاریخ واردشده معتبر نمی‌باشد (فرمت: YYYY/MM/DD).")

        session = get_session()
        try:
            exp = ClubExpense(
                title=title.strip(),
                amount=float(amount),
                expense_date_shamsi=format_shamsi(expense_date_shamsi),
                category=category.strip() if category else "متفرقه",
                description=description.strip() if description else None,
                user_id=user_id
            )
            session.add(exp)
            session.commit()
            session.refresh(exp)
            mark_data_changed()
            log_info(f"هزینه جدید ثبت شد: '{exp.title}' به مبلغ {exp.amount:,} تومان توسط کاربر {user_id}")
            return exp
        except Exception as e:
            session.rollback()
            log_error(f"خطا در ثبت هزینه: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def update_expense(expense_id: int, title: str, amount: float, expense_date_shamsi: str, category: str, description: str = "", user_id: int = None) -> bool:
        """Updates an existing club expense."""
        if not title or not title.strip():
            raise ValueError("عنوان هزینه نمی‌تواند خالی باشد.")
        if amount <= 0:
            raise ValueError("مبلغ هزینه باید بیشتر از صفر باشد.")
        if not is_valid_shamsi(expense_date_shamsi):
            raise ValueError("تاریخ واردشده معتبر نمی‌باشد.")

        session = get_session()
        try:
            exp = session.query(ClubExpense).filter(ClubExpense.id == expense_id).first()
            if not exp:
                raise ValueError("رکورد هزینه مورد نظر یافت نشد.")
            exp.title = title.strip()
            exp.amount = float(amount)
            exp.expense_date_shamsi = format_shamsi(expense_date_shamsi)
            exp.category = category.strip() if category else "متفرقه"
            exp.description = description.strip() if description else None
            if user_id is not None:
                exp.user_id = user_id
            session.commit()
            mark_data_changed()
            log_info(f"هزینه شناسه {expense_id} به‌روزرسانی شد.")
            return True
        except Exception as e:
            session.rollback()
            log_error(f"خطا در به‌روزرسانی هزینه {expense_id}: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def delete_expense(expense_id: int) -> bool:
        """Deletes a club expense by ID."""
        session = get_session()
        try:
            exp = session.query(ClubExpense).filter(ClubExpense.id == expense_id).first()
            if not exp:
                return False
            session.delete(exp)
            session.commit()
            mark_data_changed()
            log_info(f"هزینه شناسه {expense_id} با موفقیت حذف شد.")
            return True
        except Exception as e:
            session.rollback()
            log_error(f"خطا در حذف هزینه {expense_id}: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def add_tuition_payment(member_id: int, amount: float, payment_date_shamsi: str, user_id: int = None, payment_type: str = "شهریه دوره ماهانه", notes: str = "") -> TuitionPayment:
        """Records a new tuition payment."""
        if amount <= 0:
            raise ValueError("مبلغ شهریه باید بزرگتر از صفر باشد.")
        if not is_valid_shamsi(payment_date_shamsi):
            raise ValueError("تاریخ پرداخت معتبر نمی‌باشد.")

        session = get_session()
        try:
            member = session.query(Member).filter(Member.id == member_id).first()
            if not member:
                raise ValueError("ورزشکار مورد نظر یافت نشد.")
            
            # If user_id is not given, inherit from member's assigned trainer
            actual_user_id = user_id or member.user_id

            tp = TuitionPayment(
                member_id=member_id,
                user_id=actual_user_id,
                amount=float(amount),
                payment_date_shamsi=format_shamsi(payment_date_shamsi),
                payment_type=payment_type.strip() if payment_type else "شهریه دوره ماهانه",
                notes=notes.strip() if notes else None
            )
            session.add(tp)

            # Update member's current tuition fee
            member.tuition_fee = float(amount)

            # Auto-renew membership expiration date if payment is for a monthly cycle
            norm_type = (payment_type or "").strip()
            if "ماهانه" in norm_type or "دوره" in norm_type or not norm_type:
                from nemov.utils.jalali_date import get_today_shamsi, add_months_shamsi, days_until_expire
                today_sh = get_today_shamsi()
                curr_exp = member.membership_expire_shamsi
                if not curr_exp or days_until_expire(curr_exp) < 0:
                    base_d = format_shamsi(payment_date_shamsi) if payment_date_shamsi else today_sh
                else:
                    base_d = curr_exp
                member.membership_expire_shamsi = add_months_shamsi(base_d, 1)
                member.status = "active"

            session.commit()
            session.refresh(tp)
            mark_data_changed()
            log_info(f"شهریه برای عضو {member.full_name} به مبلغ {amount:,} ثبت شد.")
            return tp
        except Exception as e:
            session.rollback()
            log_error(f"خطا در ثبت شهریه: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def update_tuition_payment(payment_id: int, amount: float, payment_date_shamsi: str, payment_type: str = "شهریه دوره ماهانه", notes: str = "") -> bool:
        """Updates an existing tuition payment record."""
        if amount <= 0:
            raise ValueError("مبلغ شهریه باید بزرگتر از صفر باشد.")
        if not is_valid_shamsi(payment_date_shamsi):
            raise ValueError("تاریخ پرداخت معتبر نمی‌باشد.")

        session = get_session()
        try:
            tp = session.query(TuitionPayment).filter(TuitionPayment.id == payment_id).first()
            if not tp:
                raise ValueError("رکورد پرداخت مورد نظر یافت نشد.")
            tp.amount = float(amount)
            tp.payment_date_shamsi = format_shamsi(payment_date_shamsi)
            tp.payment_type = payment_type.strip() if payment_type else "شهریه دوره ماهانه"
            tp.notes = notes.strip() if notes else None
            session.commit()
            mark_data_changed()
            log_info(f"پرداخت شهریه شناسه {payment_id} به‌روزرسانی شد.")
            return True
        except Exception as e:
            session.rollback()
            log_error(f"خطا در به‌روزرسانی پرداخت شهریه {payment_id}: {e}")
            raise
        finally:
            session.close()

    @staticmethod
    def delete_tuition_payment(payment_id: int) -> bool:
        """Deletes a tuition payment record."""
        session = get_session()
        try:
            tp = session.query(TuitionPayment).filter(TuitionPayment.id == payment_id).first()
            if not tp:
                return False
            session.delete(tp)
            session.commit()
            mark_data_changed()
            log_info(f"پرداخت شهریه شناسه {payment_id} حذف شد.")
            return True
        except Exception as e:
            session.rollback()
            log_error(f"خطا در حذف پرداخت شهریه: {e}")
            raise
        finally:
            session.close()
