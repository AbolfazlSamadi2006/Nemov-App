from datetime import datetime
from yalda.database.connection import SessionLocal, engine
from yalda.models.database_models import Base, NotificationHistory, Member, SystemSetting
from yalda.auth.authentication import CurrentUser
from yalda.utils.jalali_date import get_today_shamsi


class NotificationService:
    _table_ensured = False

    @classmethod
    def ensure_table(cls):
        if not cls._table_ensured:
            try:
                Base.metadata.create_all(bind=engine)
                cls._table_ensured = True
            except Exception:
                pass

    @classmethod
    def _backfill_initial_history_if_needed(cls, session, today_shamsi: str):
        """
        Ensures that existing members' past/current reminders from the start of the club
        up to the current moment are recorded in notification_history on initial setup.
        """
        try:
            flag = session.query(SystemSetting).filter_by(key="notif_history_backfilled_v1").first()
            if flag and flag.value == "1":
                return

            members = session.query(Member).order_by(Member.id.asc()).all()
            for m in members:
                if m.membership_expire_shamsi and m.membership_expire_shamsi <= today_shamsi:
                    n_key = f"exp_hist_{m.id}_{m.membership_expire_shamsi}"
                    exists = session.query(NotificationHistory).filter_by(notif_key=n_key).first()
                    if not exists:
                        session.add(NotificationHistory(
                            user_id=m.user_id,
                            member_id=m.id,
                            member_name=m.full_name,
                            notif_type="expire_today",
                            title=f"🚨 موعد شهریه: {m.full_name}",
                            description=f"سررسید دوره عضویت {m.full_name} در تاریخ {m.membership_expire_shamsi}",
                            date_shamsi=m.membership_expire_shamsi,
                            notif_key=n_key,
                            is_read=True,
                            is_deleted=False
                        ))
            if not flag:
                session.add(SystemSetting(key="notif_history_backfilled_v1", value="1"))
            else:
                flag.value = "1"
            session.commit()
        except Exception:
            session.rollback()

    @classmethod
    def sync_and_get_unread_sidebar_notifications(cls):
        """
        Syncs today/tomorrow birthday & membership expiration notifications into
        notification_history, and returns only UNREAD (and non-deleted) items
        for display in the Sidebar card.
        Returns: (unread_birthdays, unread_expirations)
          where each element is a list of (member, delta, notif_id).
        """
        cls.ensure_table()
        unread_birthdays = []
        unread_expirations = []

        today_shamsi = get_today_shamsi()
        now_time = datetime.now().strftime("%H:%M")
        date_time_str = f"{today_shamsi} - {now_time}"

        from yalda.services.member_service import MemberService
        upcoming_bdays = MemberService.get_upcoming_birthday_members(days_ahead=1, include_today=True) or []
        upcoming_exps = MemberService.get_upcoming_expiration_members(days_ahead=1) or []

        session = SessionLocal()
        try:
            cls._backfill_initial_history_if_needed(session, today_shamsi)

            # 1. Process Birthday Notifications
            for item in upcoming_bdays:
                if isinstance(item, tuple):
                    member, delta = item
                else:
                    member, delta = item, 1

                if delta == 0:
                    n_type = "birthday_today"
                    raw_text = f"🎂 امروز تولد: {member.full_name}"
                    desc_text = f"امروز سالروز تولد {member.full_name} است"
                else:
                    n_type = "birthday_tomorrow"
                    raw_text = f"🎉 تولد فردا: {member.full_name}"
                    desc_text = f"فردا سالروز تولد {member.full_name} است"

                n_key = f"bday_{member.id}_{today_shamsi}_{delta}"
                rec = session.query(NotificationHistory).filter_by(notif_key=n_key).first()
                if not rec:
                    rec = NotificationHistory(
                        user_id=getattr(member, "user_id", None) or CurrentUser.get_id(),
                        member_id=member.id,
                        member_name=member.full_name,
                        notif_type=n_type,
                        title=raw_text,
                        description=desc_text,
                        date_shamsi=date_time_str,
                        notif_key=n_key,
                        is_read=False,
                        is_deleted=False
                    )
                    session.add(rec)
                    session.flush()

                if not rec.is_read and not rec.is_deleted:
                    unread_birthdays.append((member, delta, rec.id))

            # 2. Process Expiration / Tuition Notifications
            for member, delta in upcoming_exps:
                fa_exp = str(member.membership_expire_shamsi or "").translate(str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹"))
                if delta == 0:
                    n_type = "expire_today"
                    raw_text = f"🚨 موعد شهریه: {member.full_name}"
                    desc_text = f"امروز موعد تمدید شهریه {member.full_name} است — تاریخ انقضا: {fa_exp}"
                else:
                    n_type = "expire_tomorrow"
                    raw_text = f"⏳ سررسید فردا: {member.full_name}"
                    desc_text = f"فردا پایان اعتبار شهریه {member.full_name} است — تاریخ انقضا: {fa_exp}"

                n_key = f"exp_{member.id}_{member.membership_expire_shamsi}_{today_shamsi}_{delta}"
                rec = session.query(NotificationHistory).filter_by(notif_key=n_key).first()
                if not rec:
                    rec = NotificationHistory(
                        user_id=getattr(member, "user_id", None) or CurrentUser.get_id(),
                        member_id=member.id,
                        member_name=member.full_name,
                        notif_type=n_type,
                        title=raw_text,
                        description=desc_text,
                        date_shamsi=date_time_str,
                        notif_key=n_key,
                        is_read=False,
                        is_deleted=False
                    )
                    session.add(rec)
                    session.flush()

                if not rec.is_read and not rec.is_deleted:
                    unread_expirations.append((member, delta, rec.id))

            session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

        return unread_birthdays, unread_expirations

    @classmethod
    def mark_all_as_read(cls) -> int:
        """Marks all currently unread notifications for the active trainer/admin as read."""
        cls.ensure_table()
        session = SessionLocal()
        try:
            q = session.query(NotificationHistory).filter(NotificationHistory.is_read == False)
            if not CurrentUser.is_admin() and CurrentUser.get_id():
                uid = CurrentUser.get_id()
                q = q.filter((NotificationHistory.user_id == uid) | (NotificationHistory.user_id.is_(None)))
            updated = q.update({NotificationHistory.is_read: True}, synchronize_session=False)
            session.commit()
            return updated
        except Exception:
            session.rollback()
            return 0
        finally:
            session.close()

    @classmethod
    def get_history(cls) -> list:
        """Returns all non-deleted NotificationHistory records from beginning until now (newest first)."""
        cls.ensure_table()
        # Sync first so any current notifications are guaranteed to be in the table
        cls.sync_and_get_unread_sidebar_notifications()

        session = SessionLocal()
        try:
            q = session.query(NotificationHistory).filter(NotificationHistory.is_deleted == False)
            if not CurrentUser.is_admin() and CurrentUser.get_id():
                uid = CurrentUser.get_id()
                q = q.filter((NotificationHistory.user_id == uid) | (NotificationHistory.user_id.is_(None)))
            return q.order_by(NotificationHistory.id.desc()).all()
        except Exception:
            return []
        finally:
            session.close()

    @classmethod
    def delete_by_ids(cls, notif_ids: list) -> int:
        """Soft-deletes selected notifications from history (and marks them read so they don't reappear)."""
        if not notif_ids:
            return 0
        cls.ensure_table()
        session = SessionLocal()
        try:
            q = session.query(NotificationHistory).filter(NotificationHistory.id.in_(notif_ids))
            count = q.update(
                {NotificationHistory.is_deleted: True, NotificationHistory.is_read: True},
                synchronize_session=False
            )
            session.commit()
            return count
        except Exception:
            session.rollback()
            return 0
        finally:
            session.close()

    @classmethod
    def delete_all_history(cls) -> int:
        """Soft-deletes all notifications in history for the active user/admin."""
        cls.ensure_table()
        session = SessionLocal()
        try:
            q = session.query(NotificationHistory).filter(NotificationHistory.is_deleted == False)
            if not CurrentUser.is_admin() and CurrentUser.get_id():
                uid = CurrentUser.get_id()
                q = q.filter((NotificationHistory.user_id == uid) | (NotificationHistory.user_id.is_(None)))
            count = q.update(
                {NotificationHistory.is_deleted: True, NotificationHistory.is_read: True},
                synchronize_session=False
            )
            session.commit()
            return count
        except Exception:
            session.rollback()
            return 0
        finally:
            session.close()
