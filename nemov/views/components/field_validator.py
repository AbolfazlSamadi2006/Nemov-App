"""
nemov/views/components/field_validator.py
Smart Input Validation, Micro-Warning Labels and Guardrails for Nemov Form Controls.
Provides non-intrusive on-blur (lazy) validation that only warns on FocusOut / Enter / Submit.
"""
from PyQt6.QtWidgets import QLabel, QWidget, QLineEdit, QDoubleSpinBox, QSpinBox
from PyQt6.QtCore import Qt, QObject
from nemov.utils.jalali_date import parse_shamsi, get_today_shamsi, is_valid_shamsi
import re


class MicroWarningLabel(QLabel):
    """
    A compact warning label positioned below or adjacent to form inputs.
    Renders with amber warning styling and smooth hide/show.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.setStyleSheet(
            "color: #F59E0B; font-size: 10px; font-weight: bold; "
            "padding: 1px 4px; background: transparent; font-family: 'Vazirmatn';"
        )
        self.setTextFormat(Qt.TextFormat.PlainText)
        self.setWordWrap(True)
        self.setVisible(False)

    def show_warning(self, message: str):
        if message:
            self.setText(message)
            self.setVisible(True)
        else:
            self.clear_warning()

    def clear_warning(self):
        self.setText("")
        self.setVisible(False)


class FieldValidator(QObject):
    """
    Connects an input widget (QLineEdit, QDoubleSpinBox, QSpinBox) to a validation
    function and a MicroWarningLabel. Runs strictly on FocusOut / Enter (editingFinished)
    or on programmatic validate() call.
    """
    def __init__(self, widget: QWidget, validator_fn, warning_label: MicroWarningLabel = None):
        super().__init__(widget)
        self.widget = widget
        self.validator_fn = validator_fn
        self.warning_label = warning_label or MicroWarningLabel(widget.parentWidget())
        self.last_error = None

        # Connect to editingFinished (fires on FocusOut and Enter)
        if hasattr(widget, "editingFinished"):
            widget.editingFinished.connect(self.validate)

    def get_value(self):
        if isinstance(self.widget, (QDoubleSpinBox, QSpinBox)):
            return self.widget.value()
        elif isinstance(self.widget, QLineEdit):
            return self.widget.text()
        return None

    def validate(self) -> bool:
        """
        Executes validation. Updates micro-label. Returns True if valid, False if has warning.
        """
        val = self.get_value()
        err = self.validator_fn(val)
        self.last_error = err
        if err:
            self.warning_label.show_warning(err)
            return False
        else:
            self.warning_label.clear_warning()
            return True


# =========================================================================
# STANDARD REUSABLE VALIDATION LOGIC FUNCTIONS
# =========================================================================

def validate_weight(val) -> str | None:
    try:
        w = float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return None
    if w <= 0.0:
        return None  # Empty or unentered
    if w < 30.0 or w > 250.0:
        return "⚠️ وزن وارد شده غیرمعمول است."
    return None


def validate_height(val) -> str | None:
    try:
        h = float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return None
    if h <= 0.0:
        return None
    if h < 90.0 or h > 230.0:
        return "⚠️ قد وارد شده غیرمعمول است."
    return None


def validate_phone(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    s = s.translate(persian_to_eng)
    # Check phone format
    if not s.isdigit() or len(s) != 11 or not s.startswith("09"):
        return "⚠️ شماره تلفن باید ۱۱ رقم و با ۰۹ شروع شود."
    return None


def validate_birthdate_age(shamsi_date_str: str) -> str | None:
    if not shamsi_date_str or not is_valid_shamsi(shamsi_date_str):
        return None
    try:
        dt = parse_shamsi(shamsi_date_str)
        today = parse_shamsi(get_today_shamsi())
        age = today.year - dt.year - ((today.month, today.day) < (dt.month, dt.day))
        if age < 5 or age > 95:
            return "⚠️ سن ورزشکار خارج از بازه معمول است."
    except Exception:
        pass
    return None


def validate_body_fat(val) -> str | None:
    try:
        f = float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return None
    if f <= 0.0:
        return None
    if f < 3.0 or f > 60.0:
        return "⚠️ درصد چربی وارد شده غیرمعمول است."
    return None


def validate_limb_circ(val, limb_type: str = "thigh_calf") -> str | None:
    try:
        c = float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return None
    if c <= 0.0:
        return None
    if limb_type in ("thigh", "calf", "thigh_calf"):
        if c < 20.0 or c > 120.0:
            return "⚠️ دور ران/ساق خارج از محدوده طبیعی آناتومیک است."
    elif limb_type == "arm":
        if c < 15.0 or c > 70.0:
            return "⚠️ دور بازو خارج از محدوده طبیعی است."
    else:
        if c < 30.0 or c > 200.0:
            return "⚠️ اندازه وارد شده غیرمعمول است."
    return None


def validate_heart_rate(val) -> str | None:
    try:
        hr = int(val) if val is not None else 0
    except (ValueError, TypeError):
        return None
    if hr <= 0:
        return None
    if hr < 40:
        return "⚠️ ضربان قلب استراحت بسیار پایین است (برادی‌کاردی شدید)."
    elif hr > 140:
        return "⚠️ ضربان قلب استراحت بسیار بالا است (تاکی‌کاردی)."
    return None


def validate_blood_pressure(systolic, diastolic) -> str | None:
    try:
        sys = int(systolic) if systolic else 0
        dia = int(diastolic) if diastolic else 0
    except (ValueError, TypeError):
        return None
    if sys > 180 or dia > 120:
        return "⚠️ فشار خون در محدوده بحرانی است."
    return None


def validate_workout_sets(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    s = s.translate(persian_to_eng)
    try:
        num = int(s)
        if num <= 0:
            return "⚠️ تعداد ست باید بزرگتر از صفر باشد."
        if num > 8:
            return "⚠️ تعداد ست در هر حرکت بسیار بالا است."
    except ValueError:
        pass
    return None


def validate_workout_reps(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    s = s.translate(persian_to_eng)
    if "-" in s:
        # Range like "10-12"
        parts = s.split("-")
        for p in parts:
            p = p.strip()
            if p.isdigit():
                if int(p) > 100:
                    return "⚠️ تعداد تکرار در هر ست بسیار بالا است."
    else:
        try:
            num = int(s)
            if num < 0:
                return "⚠️ تعداد تکرار نمی‌تواند منفی باشد."
            if num > 100:
                return "⚠️ تعداد تکرار در هر ست بسیار بالا است."
        except ValueError:
            pass
    return None


def validate_workout_weight(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    s = s.translate(persian_to_eng)
    try:
        num = float(s)
        if num < 0:
            return "⚠️ وزنه نمی‌تواند عدد منفی باشد."
        # Positive weights are completely unrestricted per user specification!
    except ValueError:
        pass
    return None


def validate_workout_rest(val) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    if not s or s == "-":
        return None
    persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    s = s.translate(persian_to_eng)
    try:
        num = float(s)
        if num < 0:
            return "⚠️ زمان استراحت نمی‌تواند منفی باشد."
        # Positive rest is unrestricted per user specification!
    except ValueError:
        pass
    return None


def validate_daily_calories(val, bmr: float = 0.0) -> str | None:
    try:
        cal = float(val) if val is not None else 0.0
    except (ValueError, TypeError):
        return None
    if cal <= 0.0:
        return None
    if cal < 1000.0 or (bmr > 0 and cal < (bmr * 0.7)):
        return "⚠️ کالری روزانه کمتر از حد مجاز متابولیسم پایه است."
    elif cal > 6500.0:
        return "⚠️ کالری روزانه بسیار بالا و فراتر از سطح معمول است."
    return None


def validate_protein(factor: float = 0.0, total_grams: float = 0.0) -> str | None:
    # Relaxed up to 5.5 g/kg or 400g for mass-gain athletes
    if factor > 5.5 or total_grams > 400.0:
        return "⚠️ مقدار پروتئین تنظیمی بیش از حد مجاز است."
    return None


def validate_food_macros(cal: float, p: float, c: float, f: float) -> str | None:
    if cal > 900.0:
        return "⚠️ کالری ماده غذایی نمی‌تواند بیش از ۹۰۰ کیلوکالری در ۱۰۰ گرم باشد."
    if (p + c + f) > 100.5:
        return "⚠️ مجموع پروتئین، کربوهیدرات و چربی نمی‌تواند بیشتر از ۱۰۰ گرم باشد."
    return None


def validate_tuition_amount(val) -> str | None:
    if val is None:
        return None
    s = str(val).replace(",", "").replace("٬", "").strip()
    persian_to_eng = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')
    s = s.translate(persian_to_eng)
    if not s:
        return None
    try:
        amt = float(s)
        if amt <= 0:
            return "⚠️ مبلغ پرداختی باید بزرگتر از صفر باشد."
    except ValueError:
        return "⚠️ مبلغ وارد شده معتبر نیست."
    return None
