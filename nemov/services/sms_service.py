import json
import logging
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any

import config
from nemov.auth.authentication import CurrentUser
from nemov.utils.jalali_date import get_today_shamsi

logger = logging.getLogger(__name__)

# Standard Default SMS Templates aligned with approved SMS.ir templates
DEFAULT_SMS_TEMPLATES = {
    "birthday": {
        "id": "birthday",
        "title": "🎂 تبریک تولد ورزشکار",
        "template_id": 875172,
        "pattern": "ورزشکار گرامی #NAME#، زادروزتان خجسته باد! با آرزوی تندرستی، باشگاه ورزشی #GYM#",
        "variables": ["NAME", "GYM"],
        "description": "ارسال خودکار در روز تولد ورزشکار جهت ارتقای وفاداری و انگیزه"
    },
    "tuition": {
        "id": "tuition",
        "title": "🚨 یادآوری سررسید دوره عضویت",
        "template_id": 183344,
        "pattern": "ورزشکار گرامی #NAME#، اعتبار دوره عضویت شما در تاریخ #DATE# به پایان می‌رسد. جهت تمدید دوره، به مدیریت باشگاه مراجعه فرمایید. باشگاه #GYM#",
        "variables": ["NAME", "DATE", "GYM"],
        "description": "یادآوری خودکار چند روز قبل یا در روز سررسید شهریه"
    },
    "welcome": {
        "id": "welcome",
        "title": "🤝 خوش‌آمدگویی و تایید ثبت‌نام",
        "template_id": 676700,
        "pattern": "ورزشکار گرامی #NAME#، ثبت‌نام شما در باشگاه #GYM# با موفقیت انجام شد. از همراهی شما سپاسگزاریم",
        "variables": ["NAME", "GYM"],
        "description": "ارسال خودکار بلافاصله پس از ثبت عضویت جدید در باشگاه"
    },
    "holiday": {
        "id": "holiday",
        "title": "🏖️ اعلام تعطیلی باشگاه",
        "template_id": 146877,
        "pattern": "ورزشکار محترم باشگاه #GYM#، به اطلاع می‌رساند باشگاه در تاریخ #DATE# به علت #REASON# تعطیل می‌باشد.",
        "variables": ["GYM", "DATE", "REASON"],
        "description": "اطلاع‌رسانی فوری تعطیلی باشگاه در مناسبت‌های خاص یا شرایط اضطراری"
    },
    "hours": {
        "id": "hours",
        "title": "⏰ تغییر ساعت و سانس‌های باشگاه",
        "template_id": 385003,
        "pattern": "ورزشکار محترم، زمان‌بندی جدید سانس‌های باشگاه ورزشی #GYM#:\nروزها: #DAYS#\nبانوان: #WOMEN#\nآقایان: #MEN#\nتوضیحات: #NOTE#",
        "variables": ["GYM", "DAYS", "WOMEN", "MEN", "NOTE"],
        "description": "اطلاع‌رسانی تغییر زمان‌بندی سانس‌های ورزشی بانوان و آقایان"
    }
}


class SmsService:
    """
    Client-side service communicating with Cloudflare Worker SMS API Gateway.
    Zero SMS.ir API key is stored locally; all credit verification and delivery
    is proxied and centrally deducted via the serverless Cloudflare Worker.
    """

    @classmethod
    def _get_base_url(cls) -> str:
        return config.DEFAULT_CLOUD_BACKUP_URL.rstrip("/")

    @classmethod
    def _get_api_key(cls) -> str:
        return config.CLOUD_BACKUP_SECRET_KEY

    @classmethod
    def get_trainer_info(cls) -> Tuple[str, str]:
        """
        Returns (phone, full_name) guaranteed to belong to the exact same user.
        If current user has a phone, uses current user.
        Otherwise falls back to the active trainer in the database.
        """
        trainer = CurrentUser.get()
        if trainer and getattr(trainer, "phone", None):
            return str(trainer.phone).replace(" ", ""), str(trainer.full_name or "مربی")

        try:
            from nemov.database.connection import SessionLocal
            from nemov.models.database_models import User
            with SessionLocal() as session:
                # Prefer trainer role over admin when admin has no phone
                u = session.query(User).filter(User.phone.isnot(None), User.phone != "", User.role != "admin").first()
                if not u:
                    u = session.query(User).filter(User.phone.isnot(None), User.phone != "").first()
                if u:
                    return str(u.phone).replace(" ", ""), str(u.full_name or "مربی")
        except Exception:
            pass
        return "", (str(trainer.full_name) if trainer and getattr(trainer, "full_name", None) else "مربی")

    @classmethod
    def get_trainer_phone(cls) -> str:
        phone, _ = cls.get_trainer_info()
        return phone

    @classmethod
    def get_trainer_name(cls) -> str:
        _, name = cls.get_trainer_info()
        return name

    @classmethod
    def get_balance(cls, trainer_phone: str = None) -> Dict[str, Any]:
        """
        Fetches the current SMS balance and wallet status for the trainer.
        Returns: { success, phone, trainer_name, remaining, total_credited, total_used, status, last_recharge_shamsi }
        """
        phone = (trainer_phone or cls.get_trainer_phone()).replace(" ", "")
        if not phone:
            return {"success": False, "remaining": 0, "detail": "شماره موبایل مربی یافت نشد."}

        trainer_name = cls.get_trainer_name()
        gym_name = config.APP_NAME
        query = urllib.parse.urlencode({
            "phone": phone,
            "trainer_name": trainer_name,
            "gym_name": gym_name
        })
        url = f"{cls._get_base_url()}/api/sms/balance?{query}"
        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("X-API-Key", cls._get_api_key())
            req.add_header("User-Agent", "YaldaGymApp-Client/3.2")

            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                return {"success": False, "remaining": 0, "detail": err_data.get("detail", str(e))}
            except Exception:
                return {"success": False, "remaining": 0, "detail": f"خطای سرور: {e.code}"}
        except Exception as e:
            logger.warning(f"Error fetching SMS balance: {e}")
            return {"success": False, "remaining": 0, "detail": f"خطا در اتصال به سرور: {str(e)}"}

    @staticmethod
    def normalize_phone_number(raw_phone: str) -> str:
        """
        Normalizes Iranian mobile numbers to standard 11-digit ASCII format '09XXXXXXXXX'.
        Converts Persian and Arabic digits, strips spaces/dashes/delimiters,
        and standardizes +98 or 0098 prefixes.
        """
        if not raw_phone:
            return ""
        persian_arabic_digits = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")
        clean = str(raw_phone).translate(persian_arabic_digits)
        clean = "".join(ch for ch in clean if ch.isdigit() or ch == "+")
        if clean.startswith("+98"):
            clean = "0" + clean[3:]
        elif clean.startswith("0098"):
            clean = "0" + clean[4:]
        elif clean.startswith("98") and len(clean) == 12:
            clean = "0" + clean[2:]
        elif clean.startswith("9") and len(clean) == 10:
            clean = "0" + clean
        return clean

    @classmethod
    def send_single_sms(
        cls,
        recipient_phone: str,
        template_id: Optional[int] = None,
        parameters: Optional[List[Dict[str, str]]] = None,
        message_text: str = "",
        member_name: str = "",
        message_type: str = "custom",
        trainer_phone: str = None,
        trainer_name: str = None
    ) -> Tuple[bool, str, int]:
        """
        Sends an SMS through the Cloudflare Worker Gateway.
        Returns (success: bool, detail_message: str, remaining_balance: int).
        """
        phone = cls.normalize_phone_number(trainer_phone or cls.get_trainer_phone())
        t_name = trainer_name or cls.get_trainer_name()
        clean_recipient = cls.normalize_phone_number(recipient_phone)

        if not phone:
            return False, "شماره تماس مربی برای احراز هویت ثبت نشده است.", 0
        if not clean_recipient:
            return False, "شماره همراه گیرنده خالی است.", 0

        url = f"{cls._get_base_url()}/api/sms/send"
        payload = {
            "phone": phone,
            "trainer_name": t_name,
            "recipient": clean_recipient,
            "member_name": member_name,
            "type": message_type,
            "template_id": template_id,
            "parameters": parameters or [],
            "message_text": message_text
        }

        try:
            req_data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            req = urllib.request.Request(url, data=req_data, method="POST")
            req.add_header("Content-Type", "application/json; charset=utf-8")
            req.add_header("X-API-Key", cls._get_api_key())
            req.add_header("User-Agent", "YaldaGymApp-Client/3.1")

            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                rem = data.get("remaining", 0)
                return True, data.get("message", "پیامک با موفقیت ارسال شد."), rem
        except urllib.error.HTTPError as e:
            try:
                err_data = json.loads(e.read().decode("utf-8"))
                rem = err_data.get("remaining", 0)
                detail = err_data.get("detail", f"خطای سرور: {e.code}")
                return False, detail, rem
            except Exception:
                return False, f"خطای سرور ({e.code})", 0
        except Exception as e:
            logger.error(f"Error sending SMS via gateway: {e}")
            return False, f"خطای ارتباط با سرور ابری: {str(e)}", 0

    @classmethod
    def get_history(cls, trainer_phone: str = None) -> List[Dict[str, Any]]:
        """
        Retrieves the recent SMS delivery history for this trainer from the Cloudflare Worker.
        """
        phone = (trainer_phone or cls.get_trainer_phone()).replace(" ", "")
        user = CurrentUser.get()
        is_admin = bool(user and getattr(user, "role", "") == "admin")

        if is_admin and not trainer_phone:
            url = f"{cls._get_base_url()}/api/sms/history"
        elif phone:
            url = f"{cls._get_base_url()}/api/sms/history?phone={urllib.parse.quote(phone)}"
        else:
            return []

        try:
            req = urllib.request.Request(url, method="GET")
            req.add_header("X-API-Key", cls._get_api_key())
            req.add_header("User-Agent", "YaldaGymApp-Client/3.2")
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("logs", [])
        except Exception as e:
            logger.warning(f"Error fetching SMS history: {e}")
            return []

    # =========================================================================
    # Auto-Trigger Helpers (Birthday & Tuition Expiry)
    # =========================================================================

    @classmethod
    def check_and_send_automated_birthdays(cls) -> Dict[str, Any]:
        """
        Checks if auto birthday SMS is enabled. If enabled, sends birthday greetings
        for members whose birthday is today and records the send to avoid duplicates.
        """
        from nemov.database.connection import SessionLocal
        from nemov.models.database_models import SystemSetting
        from nemov.services.member_service import MemberService

        session = SessionLocal()
        try:
            flag = session.query(SystemSetting).filter_by(key="sms_auto_birthday_enabled").first()
            if not flag or flag.value != "1":
                return {"executed": False, "sent_count": 0, "reason": "غیرفعال توسط مربی"}

            today_shamsi = get_today_shamsi()
            upcoming = MemberService.get_upcoming_birthday_members(days_ahead=0, include_today=True) or []
            if not upcoming:
                return {"executed": True, "sent_count": 0, "detail": "امروز تولدی وجود ندارد."}

            trainer_phone = cls.get_trainer_phone()
            trainer_name = cls.get_trainer_name()
            gym_name = config.APP_NAME

            sent_count = 0
            for item in upcoming:
                member = item[0] if isinstance(item, tuple) else item
                if not member or not member.phone:
                    continue

                check_key = f"sms_sent_bday_{member.id}_{today_shamsi}"
                already_sent = session.query(SystemSetting).filter_by(key=check_key).first()
                if already_sent:
                    continue

                # Prepare parameters for SMS.ir template
                params = [
                    {"name": "NAME", "value": member.full_name},
                    {"name": "GYM", "value": gym_name}
                ]
                ok, msg, rem = cls.send_single_sms(
                    recipient_phone=member.phone,
                    template_id=DEFAULT_SMS_TEMPLATES["birthday"]["template_id"],
                    parameters=params,
                    message_text=f"ورزشکار گرامی {member.full_name}، زادروزتان خجسته باد! با آرزوی تندرستی، باشگاه ورزشی {gym_name}",
                    member_name=member.full_name,
                    message_type="birthday",
                    trainer_phone=trainer_phone,
                    trainer_name=trainer_name
                )
                if ok:
                    sent_count += 1
                    session.add(SystemSetting(key=check_key, value="1"))
                    session.commit()
                else:
                    logger.warning(f"Failed to send birthday SMS to {member.full_name}: {msg}")
                    if rem <= 0:
                        break # Out of balance

            return {"executed": True, "sent_count": sent_count}
        except Exception as e:
            session.rollback()
            return {"executed": False, "error": str(e)}
        finally:
            session.close()

    @classmethod
    def check_and_send_automated_tuitions(cls) -> Dict[str, Any]:
        """
        Checks if auto tuition reminder SMS is enabled. If enabled, sends reminders
        for members whose membership expires today/tomorrow and records the send.
        """
        from nemov.database.connection import SessionLocal
        from nemov.models.database_models import SystemSetting
        from nemov.services.member_service import MemberService

        session = SessionLocal()
        try:
            flag = session.query(SystemSetting).filter_by(key="sms_auto_tuition_enabled").first()
            if not flag or flag.value != "1":
                return {"executed": False, "sent_count": 0, "reason": "غیرفعال توسط مربی"}

            days_ahead_setting = session.query(SystemSetting).filter_by(key="sms_auto_tuition_days").first()
            days_ahead = int(days_ahead_setting.value) if days_ahead_setting and days_ahead_setting.value.isdigit() else 1

            today_shamsi = get_today_shamsi()
            upcoming = MemberService.get_upcoming_expiration_members(days_ahead=days_ahead) or []
            if not upcoming:
                return {"executed": True, "sent_count": 0, "detail": "موردی برای سررسید شهریه نیست."}

            trainer_phone = cls.get_trainer_phone()
            trainer_name = cls.get_trainer_name()
            gym_name = config.APP_NAME

            sent_count = 0
            for item in upcoming:
                member = item[0] if isinstance(item, tuple) else item
                if not member or not member.phone:
                    continue

                check_key = f"sms_sent_exp_{member.id}_{member.membership_expire_shamsi}"
                already_sent = session.query(SystemSetting).filter_by(key=check_key).first()
                if already_sent:
                    continue

                params = [
                    {"name": "NAME", "value": member.full_name},
                    {"name": "DATE", "value": member.membership_expire_shamsi or today_shamsi},
                    {"name": "GYM", "value": gym_name}
                ]
                ok, msg, rem = cls.send_single_sms(
                    recipient_phone=member.phone,
                    template_id=DEFAULT_SMS_TEMPLATES["tuition"]["template_id"],
                    parameters=params,
                    message_text=f"ورزشکار گرامی {member.full_name}، اعتبار دوره عضویت شما در تاریخ {member.membership_expire_shamsi} به پایان می‌رسد. جهت تمدید دوره، به مدیریت باشگاه مراجعه فرمایید. باشگاه {gym_name}",
                    member_name=member.full_name,
                    message_type="tuition",
                    trainer_phone=trainer_phone,
                    trainer_name=trainer_name
                )
                if ok:
                    sent_count += 1
                    session.add(SystemSetting(key=check_key, value="1"))
                    session.commit()
                else:
                    logger.warning(f"Failed to send tuition SMS to {member.full_name}: {msg}")
                    if rem <= 0:
                        break # Out of balance

            return {"executed": True, "sent_count": sent_count}
        except Exception as e:
            session.rollback()
            return {"executed": False, "error": str(e)}
        finally:
            session.close()

    @classmethod
    def send_welcome_sms_if_enabled(cls, member_name: str, member_phone: str) -> Tuple[bool, str]:
        """
        Sends an automated welcome SMS to a newly registered member if enabled in settings.
        """
        from nemov.database.connection import SessionLocal
        from nemov.models.database_models import SystemSetting

        clean_phone = (member_phone or "").replace(" ", "").replace("-", "")
        if not clean_phone or clean_phone == "-":
            return False, "شماره موبایل ثبت نشده است."

        session = SessionLocal()
        try:
            flag = session.query(SystemSetting).filter_by(key="sms_auto_welcome_enabled").first()
            if not flag or flag.value != "1":
                return False, "ارسال خودکار خوش‌آمدگویی غیرفعال است."

            trainer_phone = cls.get_trainer_phone()
            trainer_name = cls.get_trainer_name()
            gym_name = config.APP_NAME

            params = [
                {"name": "NAME", "value": member_name},
                {"name": "GYM", "value": gym_name}
            ]
            ok, msg, rem = cls.send_single_sms(
                recipient_phone=clean_phone,
                template_id=DEFAULT_SMS_TEMPLATES["welcome"]["template_id"],
                parameters=params,
                message_text=f"ورزشکار گرامی {member_name}، ثبت‌نام شما در باشگاه {gym_name} با موفقیت انجام شد. از همراهی شما سپاسگزاریم",
                member_name=member_name,
                message_type="welcome",
                trainer_phone=trainer_phone,
                trainer_name=trainer_name
            )
            return ok, msg
        except Exception as e:
            logger.warning(f"Error sending auto welcome SMS to {member_name}: {e}")
            return False, str(e)
        finally:
            session.close()
