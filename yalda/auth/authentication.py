from datetime import datetime
from yalda.database.connection import get_session, mark_data_changed
from yalda.models.database_models import User, SystemSetting
from yalda.utils.security import verify_password, hash_password

class CurrentUser:
    _user = None

    @classmethod
    def set(cls, user: User):
        cls._user = user

    @classmethod
    def get(cls) -> User:
        return cls._user

    @classmethod
    def get_id(cls) -> int:
        return cls._user.id if cls._user else None

    @classmethod
    def logout(cls):
        cls._user = None

    @classmethod
    def is_admin(cls) -> bool:
        return cls._user is not None and cls._user.role == "admin"

    @classmethod
    def is_trainer(cls) -> bool:
        return cls._user is not None and cls._user.role in ["admin", "trainer"]

PERSIAN_ARABIC_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

def normalize_digits(s: str) -> str:
    if not s:
        return ""
    return s.translate(PERSIAN_ARABIC_DIGITS).strip()

def is_app_license_active() -> bool:
    """Checks if the application license/registration status is Active."""
    session = get_session()
    try:
        setting = session.query(SystemSetting).filter(SystemSetting.key == "app_license_active").first()
        if setting and setting.value and setting.value.lower() == "true":
            return True
        return False
    finally:
        session.close()

def set_app_license_active(active: bool):
    """Sets the application license/registration status (Admin only)."""
    session = get_session()
    try:
        setting = session.query(SystemSetting).filter(SystemSetting.key == "app_license_active").first()
        if not setting:
            setting = SystemSetting(key="app_license_active", value="true" if active else "false")
            session.add(setting)
        else:
            setting.value = "true" if active else "false"
        session.commit()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_developer_info() -> dict:
    """Returns developer information from SystemSetting table (with defaults)."""
    import config
    default_photo = str(config.BASE_DIR / "resources" / "images" / "developer_photo.jpg")

    defaults = {
        "first_name": "ابوالفضل",
        "last_name": "صمدی کوچکسرائی",
        "phone": "09336427711",
        "email": "a.samadi2006@gmail.com",
        "github": "github.com/AbolfazlSamadi2006",
        "telegram": "t.me/AqaSamadi",
        "photo_path": default_photo
    }

    session = get_session()
    try:
        settings = session.query(SystemSetting).filter(SystemSetting.key.like("dev_%")).all()
        for s in settings:
            key_name = s.key.replace("dev_", "")
            if key_name in defaults and s.value:
                defaults[key_name] = s.value
        return defaults
    finally:
        session.close()

def set_developer_info(data: dict):
    """Saves developer information into SystemSetting table (Admin only)."""
    session = get_session()
    try:
        for k, v in data.items():
            db_key = f"dev_{k}"
            setting = session.query(SystemSetting).filter(SystemSetting.key == db_key).first()
            if not setting:
                setting = SystemSetting(key=db_key, value=str(v) if v is not None else "")
                session.add(setting)
            else:
                setting.value = str(v) if v is not None else ""
        session.commit()
        mark_data_changed()
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()


def authenticate_user(username: str, password: str) -> User:
    """Authenticates username and password (with dynamic 2006+time master override for admin)."""
    session = get_session()
    try:
        username = normalize_digits(username).lower()
        password = normalize_digits(password)

        now = datetime.now()
        # Admin dynamic password requirement: 2006 + current clock time (HHMM) with +-2 mins tolerance
        from datetime import timedelta
        valid_time_passwords = {"2006"}  # Emergency static backup password
        for offset in [-2, -1, 0, 1, 2]:
            t = now + timedelta(minutes=offset)
            h24 = t.strftime("%H%M")
            h12 = t.strftime("%I%M")
            h24_single = f"{t.hour}{t.minute:02d}"
            h12_single = f"{(t.hour % 12 or 12)}{t.minute:02d}"
            valid_time_passwords.add(f"2006{h24}")
            valid_time_passwords.add(f"2006{h12}")
            valid_time_passwords.add(f"2006{h24_single}")
            valid_time_passwords.add(f"2006{h12_single}")

        # Master Admin Auth using 2006 + current clock time
        if username == "admin" and password in valid_time_passwords:

            admin_user = session.query(User).filter(User.username == "admin").first()
            if not admin_user:
                admin_user = session.query(User).first()
            if not admin_user:
                admin_user = User(
                    username="admin",
                    password_hash=hash_password("admin123"),
                    first_name="مدیر",
                    last_name="سیستم",
                    full_name="مدیر سیستم",
                    role="admin"
                )
                session.add(admin_user)
                session.commit()
            CurrentUser.set(admin_user)
            return admin_user

        # Regular user authentication against SQLite DB
        user = session.query(User).filter(User.username == username, User.is_active == True).first()
        if user and verify_password(password, user.password_hash):
            CurrentUser.set(user)
            return user

        return None
    finally:
        session.close()

def check_username_exists(username: str) -> bool:
    """Checks if a username exists in the active users table."""
    session = get_session()
    try:
        username = normalize_digits(username).lower()
        if username == "admin":
            return True
        user = session.query(User).filter(User.username == username, User.is_active == True).first()
        return user is not None
    finally:
        session.close()

def verify_recovery_credentials(phone: str, recovery_code: str) -> User:
    """Verifies trainer account recovery using both phone number and secret recovery code."""
    session = get_session()
    try:
        norm_phone = normalize_digits(phone)
        norm_code = normalize_digits(recovery_code)

        users = session.query(User).filter(User.is_active == True).all()
        for u in users:
            u_phone = normalize_digits(u.phone)
            u_code = normalize_digits(u.recovery_code)
            if u_phone and u_code and u_phone == norm_phone and u_code == norm_code:
                return u
        return None
    finally:
        session.close()

def register_trainer(first_name: str, last_name: str, phone: str, birth_date_shamsi: str, username: str, password: str, recovery_code: str, photo_path: str = None, email: str = None) -> User:
    """Registers a new trainer account in the system."""
    session = get_session()
    try:
        clean_user = normalize_digits(username).lower()
        existing = session.query(User).filter(User.username == clean_user).first()
        if existing:
            raise ValueError("این نام کاربری قبلاً ثبت شده است. لطفاً نام کاربری دیگری انتخاب کنید.")

        new_trainer = User(
            username=clean_user,
            password_hash=hash_password(password),
            plain_password=password.strip() if password else None,
            first_name=first_name.strip(),
            last_name=last_name.strip(),
            full_name=f"{first_name.strip()} {last_name.strip()}",
            phone=normalize_digits(phone),
            email=email.strip().lower() if (email and email.strip()) else None,
            birth_date_shamsi=birth_date_shamsi.strip() if birth_date_shamsi else None,
            photo_path=photo_path,
            recovery_code=normalize_digits(recovery_code),
            role="trainer",
            is_active=True
        )
        session.add(new_trainer)
        session.commit()
        session.refresh(new_trainer)
        mark_data_changed()
        return new_trainer
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def get_all_trainers() -> list:
    """Returns a list of all registered trainers and their member counts (for Admin)."""
    session = get_session()
    try:
        from yalda.models.database_models import User, Member
        users = session.query(User).filter(User.username != "admin", User.role != "admin").all()
        results = []
        for u in users:
            m_count = session.query(Member).filter(Member.user_id == u.id).count()
            results.append({
                "id": u.id,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "full_name": u.display_name,
                "username": u.username,
                "password": u.plain_password or "-",
                "phone": u.phone or "-",
                "email": u.email or "-",
                "birth_date_shamsi": u.birth_date_shamsi or "-",
                "recovery_code": u.recovery_code or "-",
                "photo_path": u.photo_path or "",
                "member_count": m_count
            })
        return results
    finally:
        session.close()

def find_user_by_email_or_phone(identity: str) -> User:
    """Finds a user by email, phone, or username for recovery purposes."""
    if not identity:
        return None
    session = get_session()
    try:
        ident_clean = identity.strip().lower()
        ident_digits = normalize_digits(identity).strip()

        # Check by email
        user = session.query(User).filter(User.email.isnot(None), User.email == ident_clean).first()
        if user:
            return user

        # Check by phone
        if ident_digits:
            user = session.query(User).filter(User.phone.isnot(None), User.phone == ident_digits).first()
            if user:
                return user

        # Check by username
        user = session.query(User).filter(User.username == ident_clean).first()
        return user
    finally:
        session.close()

def update_trainer_profile(user_id: int, first_name: str, last_name: str, phone: str, birth_date_shamsi: str, photo_path: str, username: str, password: str = None, recovery_code: str = None, new_password: str = None, email: str = None) -> bool:
    """Updates trainer's profile and credentials."""
    session = get_session()
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False

        if username:
            clean_username = normalize_digits(username).lower()
            # check if taken by another user
            other = session.query(User).filter(User.username == clean_username, User.id != user_id).first()
            if other:
                raise ValueError("این نام کاربری توسط کاربر دیگری ثبت شده است.")
            user.username = clean_username

        if first_name:
            user.first_name = first_name.strip()
        if last_name:
            user.last_name = last_name.strip()
        user.full_name = f"{user.first_name or ''} {user.last_name or ''}".strip() or user.username

        if phone:
            user.phone = normalize_digits(phone)
        if email is not None:
            user.email = email.strip().lower() if email.strip() else None
        if birth_date_shamsi:
            user.birth_date_shamsi = birth_date_shamsi.strip()
        if photo_path is not None:
            user.photo_path = photo_path

        effective_password = password or new_password
        if effective_password:
            user.password_hash = hash_password(effective_password.strip())
            user.plain_password = effective_password.strip()
        if recovery_code:
            user.recovery_code = normalize_digits(recovery_code)

        session.commit()
        mark_data_changed()
        # update current user session object
        if CurrentUser.get_id() == user_id:
            CurrentUser.set(user)
        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

def update_user_credentials(new_username: str, new_password: str = None) -> bool:
    """Legacy helper function for updating credentials."""
    current_u = CurrentUser.get()
    if not current_u:
        return False
    return update_trainer_profile(
        user_id=current_u.id,
        first_name=current_u.first_name,
        last_name=current_u.last_name,
        phone=current_u.phone,
        birth_date_shamsi=current_u.birth_date_shamsi,
        photo_path=current_u.photo_path,
        username=new_username,
        password=new_password,
        recovery_code=current_u.recovery_code
    )

def delete_trainer_account(user_id: int) -> bool:
    """Completely deletes a trainer account and all their associated members, plans, and files."""
    session = get_session()
    try:
        from yalda.models.database_models import User, Member, WorkoutPlan, NutritionPlan
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        if user.username == "admin" or user.role == "admin":
            raise ValueError("حساب مدیر ارشد سیستم قابل حذف نمی‌باشد.")
            
        trainer_phone = user.phone

        # 1. Delete all members belonging to this trainer
        members = session.query(Member).filter(Member.user_id == user_id).all()
        for m in members:
            # Delete member files
            if m.photo_path and os.path.exists(m.photo_path):
                try:
                    os.remove(m.photo_path)
                except Exception:
                    pass
            session.delete(m)

        # 2. Delete workout & nutrition plans created by this trainer
        workout_plans = session.query(WorkoutPlan).filter(WorkoutPlan.created_by_user_id == user_id).all()
        for wp in workout_plans:
            session.delete(wp)
            
        nutrition_plans = session.query(NutritionPlan).filter(NutritionPlan.created_by_user_id == user_id).all()
        for np in nutrition_plans:
            session.delete(np)

        # 3. Delete trainer photo
        if user.photo_path and os.path.exists(user.photo_path):
            try:
                os.remove(user.photo_path)
            except Exception:
                pass

        # 4. Delete the User record
        session.delete(user)
        session.commit()
        mark_data_changed()

        # 5. Overwrite/Sync local backup
        try:
            from yalda.services.backup_service import create_local_backup
            create_local_backup()
        except Exception:
            pass

        # 6. Delete backup on Cloudflare Worker if connected
        if trainer_phone:
            try:
                import urllib.request, config
                clean_phone = "".join(filter(str.isdigit, trainer_phone))
                if clean_phone and config.DEFAULT_CLOUD_BACKUP_URL:
                    del_url = f"{config.DEFAULT_CLOUD_BACKUP_URL.rstrip('/')}/api/backup/delete/{clean_phone}"
                    req = urllib.request.Request(del_url, method="POST")
                    req.add_header("X-API-Key", config.CLOUD_BACKUP_SECRET_KEY)
                    req.add_header("User-Agent", "YaldaGymDesktop/2.1.0")
                    urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass

        return True
    except Exception as e:
        session.rollback()
        raise e
    finally:
        session.close()

