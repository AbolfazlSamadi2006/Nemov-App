from nemov.database.connection import get_session, mark_data_changed
from nemov.models.database_models import Member, HealthRecord, MedicalDocument
from nemov.utils.jalali_date import get_today_shamsi, is_membership_active
from sqlalchemy import or_

class MemberService:
    @staticmethod
    def get_all_members(search_query: str = None, status_filter: str = "all", user_id: int = None):

        session = get_session()
        try:
            from nemov.auth.authentication import CurrentUser
            query = session.query(Member)

            # Scoping: If user is admin, show ALL members. Otherwise scope to trainer.
            if not CurrentUser.is_admin():
                curr_user_id = user_id or CurrentUser.get_id()
                if curr_user_id:
                    query = query.filter(or_(Member.user_id == curr_user_id, Member.user_id == None))


            if search_query:
                pattern = f"%{search_query.strip()}%"
                query = query.filter(
                    or_(
                        Member.first_name.like(pattern),
                        Member.last_name.like(pattern),
                        Member.phone.like(pattern)
                    )
                )

            members = query.order_by(Member.id.desc()).all()
            
            # Check for active vs expired vs archived memberships dynamically
            from nemov.utils.jalali_date import days_until_expire
            db_dirty = False
            for m in members:
                old_status = m.status
                if m.status == "archived" or not m.membership_start_shamsi or not m.membership_start_shamsi.strip():
                    m.status = "archived"
                elif m.membership_expire_shamsi:
                    if is_membership_active(m.membership_expire_shamsi):
                        m.status = "active"
                    else:
                        m.status = "expired"
                if m.status != old_status:
                    db_dirty = True

            if db_dirty:
                session.commit()

            if status_filter and status_filter != "all":
                if status_filter == "expiring_soon":
                    members = [
                        m for m in members
                        if m.status == "active" and 0 <= days_until_expire(m.membership_expire_shamsi) <= 5
                    ]
                else:
                    members = [m for m in members if m.status == status_filter]

            return members
        finally:
            session.close()

    @staticmethod
    def get_member_by_id(member_id: int):
        session = get_session()
        try:
            member = session.query(Member).filter(Member.id == member_id).first()
            if member:
                if member.status == "archived" or not member.membership_start_shamsi or not member.membership_start_shamsi.strip():
                    member.status = "archived"
                elif member.membership_expire_shamsi:
                    if is_membership_active(member.membership_expire_shamsi):
                        member.status = "active"
                    else:
                        member.status = "expired"
            return member
        finally:
            session.close()

    @staticmethod
    def create_member(data: dict) -> Member:
        session = get_session()
        try:
            h_val = float(data.get("height_cm")) if data.get("height_cm") is not None and float(data.get("height_cm", 0)) > 0 else None
            w_val = float(data.get("initial_weight_kg")) if data.get("initial_weight_kg") is not None and float(data.get("initial_weight_kg", 0)) > 0 else None
            
            exp_date = data.get("membership_expire_shamsi")
            start_date = data.get("membership_start_shamsi")
            requested_status = data.get("status", "active")

            if requested_status == "archived" or not start_date or not str(start_date).strip():
                status_val = "archived"
            elif exp_date and not is_membership_active(exp_date):
                status_val = "expired"
            else:
                status_val = "active"

            from nemov.auth.authentication import CurrentUser
            curr_user_id = data.get("user_id") or CurrentUser.get_id()

            member = Member(
                user_id=curr_user_id,
                first_name=data.get("first_name"),
                last_name=data.get("last_name"),
                phone=data.get("phone"),
                gender=data.get("gender", "male"),
                job=data.get("job"),
                birth_date_shamsi=data.get("birth_date_shamsi"),
                height_cm=h_val,
                initial_weight_kg=w_val,
                activity_level=data.get("activity_level", "moderately_active"),
                registration_date_shamsi=data.get("registration_date_shamsi") or get_today_shamsi(),
                insurance_date_shamsi=data.get("insurance_date_shamsi"),
                tuition_fee=float(data.get("tuition_fee", 0.0) or 0.0) if data.get("tuition_fee") is not None else None,
                membership_type=data.get("membership_type", "12_sessions"),
                membership_start_shamsi=start_date,
                membership_expire_shamsi=exp_date,
                photo_path=data.get("photo_path"),
                notes=data.get("notes"),
                status=status_val
            )

            session.add(member)
            session.flush()

            # Create default empty health record
            health_rec = HealthRecord(member_id=member.id)
            session.add(health_rec)

            session.commit()
            mark_data_changed()
            return member
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def update_member(member_id: int, data: dict):
        session = get_session()
        try:
            member = session.query(Member).filter(Member.id == member_id).first()
            if not member:
                raise ValueError("ورزشکار یافت نشد.")
            
            for key, val in data.items():
                if hasattr(member, key):
                    setattr(member, key, val)
            
            if member.status == "archived" or not member.membership_start_shamsi or not member.membership_start_shamsi.strip():
                member.status = "archived"
            elif member.membership_expire_shamsi:
                if is_membership_active(member.membership_expire_shamsi):
                    member.status = "active"
                else:
                    member.status = "expired"

            session.commit()
            mark_data_changed()
            return member
        finally:
            session.close()

    @staticmethod
    def archive_member(member_id: int):
        return MemberService.update_member(member_id, {"status": "archived"})


    @staticmethod
    def delete_member(member_id: int):
        session = get_session()
        try:
            from nemov.models.database_models import WorkoutAssignment, NutritionAssignment, WorkoutPlan, NutritionPlan
            member = session.query(Member).filter(Member.id == member_id).first()
            if member:
                # Find plan IDs associated with member's assignments before deletion
                w_plan_ids = [a.plan_id for a in member.workout_assignments]
                n_plan_ids = [a.plan_id for a in member.nutrition_assignments]

                session.delete(member)
                session.flush()

                # Clean up orphan workout plans
                for pid in w_plan_ids:
                    if session.query(WorkoutAssignment).filter(WorkoutAssignment.plan_id == pid).count() == 0:
                        orphan_w = session.query(WorkoutPlan).filter(WorkoutPlan.id == pid).first()
                        if orphan_w:
                            session.delete(orphan_w)

                # Clean up orphan nutrition plans
                for pid in n_plan_ids:
                    if session.query(NutritionAssignment).filter(NutritionAssignment.plan_id == pid).count() == 0:
                        orphan_n = session.query(NutritionPlan).filter(NutritionPlan.id == pid).first()
                        if orphan_n:
                            session.delete(orphan_n)

                session.commit()
                mark_data_changed()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def get_health_record(member_id: int) -> HealthRecord:
        session = get_session()
        try:
            rec = session.query(HealthRecord).filter(HealthRecord.member_id == member_id).first()
            if not rec:
                rec = HealthRecord(member_id=member_id)
                session.add(rec)
                session.commit()
            return rec
        finally:
            session.close()

    @staticmethod
    def update_health_record(member_id: int, data: dict):
        session = get_session()
        try:
            rec = session.query(HealthRecord).filter(HealthRecord.member_id == member_id).first()
            if not rec:
                rec = HealthRecord(member_id=member_id)
                session.add(rec)
            
            for key, val in data.items():
                if hasattr(rec, key):
                    setattr(rec, key, val)
            
            session.commit()
            mark_data_changed()
            return rec
        finally:
            session.close()

    @staticmethod
    def get_medical_documents(member_id: int):
        session = get_session()
        try:
            return session.query(MedicalDocument).filter(MedicalDocument.member_id == member_id).order_by(MedicalDocument.id.desc()).all()
        finally:
            session.close()

    @staticmethod
    def add_medical_document(member_id: int, title: str, file_path, notes: str = None) -> MedicalDocument:
        session = get_session()
        try:
            if isinstance(file_path, (list, tuple)):
                path_str = "||".join([str(p).strip() for p in file_path if p])
            else:
                path_str = str(file_path or "").strip()

            doc = MedicalDocument(
                member_id=member_id,
                title=title,
                file_path=path_str,
                created_at_shamsi=get_today_shamsi(),
                notes=notes
            )
            session.add(doc)
            session.commit()
            mark_data_changed()
            return doc
        finally:
            session.close()

    @staticmethod
    def delete_medical_document(doc_id: int) -> bool:
        session = get_session()
        try:
            doc = session.query(MedicalDocument).filter(MedicalDocument.id == doc_id).first()
            if doc:
                session.delete(doc)
                session.commit()
                mark_data_changed()
                return True
            return False
        finally:
            session.close()

    @staticmethod
    def get_upcoming_birthday_members(days_ahead: int = 1, include_today: bool = True):
        """Returns active members whose birthday is today (delta=0) or in `days_ahead` days (delta=1).
        Returns a list of tuples: [(member, delta), ...]
        """
        import jdatetime
        from nemov.utils.jalali_date import parse_shamsi

        session = get_session()
        try:
            from nemov.auth.authentication import CurrentUser

            query = session.query(Member).filter(Member.status == "active")
            if not CurrentUser.is_admin():
                curr_user_id = CurrentUser.get_id()
                if curr_user_id:
                    query = query.filter(or_(Member.user_id == curr_user_id, Member.user_id == None))
            members = query.all()

            today = jdatetime.date.today()
            target_date = today + jdatetime.timedelta(days=days_ahead)

            upcoming = []
            for m in members:
                if not m.birth_date_shamsi:
                    continue
                try:
                    b_date = parse_shamsi(m.birth_date_shamsi)
                    if include_today and b_date.month == today.month and b_date.day == today.day:
                        upcoming.append((m, 0))
                    elif b_date.month == target_date.month and b_date.day == target_date.day:
                        upcoming.append((m, days_ahead))
                except Exception:
                    continue
            return upcoming
        finally:
            session.close()

    @staticmethod
    def get_upcoming_expiration_members(days_ahead: int = 1):
        """Returns members whose membership expires in `days_ahead` days (or today if 0 days left)."""
        from nemov.utils.jalali_date import days_until_expire

        session = get_session()
        try:
            from nemov.auth.authentication import CurrentUser

            query = session.query(Member).filter(Member.status.in_(["active", "expired"]))
            if not CurrentUser.is_admin():
                curr_user_id = CurrentUser.get_id()
                if curr_user_id:
                    query = query.filter(or_(Member.user_id == curr_user_id, Member.user_id == None))
            members = query.all()

            upcoming = []
            for m in members:
                if not m.membership_expire_shamsi:
                    continue
                try:
                    delta = days_until_expire(m.membership_expire_shamsi)
                    # Check for 1 day left or today
                    if delta == days_ahead or (days_ahead == 1 and delta == 0):
                        upcoming.append((m, delta))
                except Exception:
                    continue
            return upcoming
        finally:
            session.close()

