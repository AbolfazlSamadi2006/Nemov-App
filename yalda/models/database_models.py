from datetime import datetime
from sqlalchemy import (
    Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class SystemSetting(Base):
    __tablename__ = "system_settings"

    key = Column(String(50), primary_key=True)
    value = Column(String(255), nullable=True)

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    plain_password = Column(String(100), nullable=True)
    first_name = Column(String(50), nullable=True)
    last_name = Column(String(50), nullable=True)
    full_name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(120), nullable=True)
    birth_date_shamsi = Column(String(10), nullable=True)
    photo_path = Column(String(255), nullable=True)
    recovery_code = Column(String(100), nullable=True)
    role = Column(String(20), nullable=False, default="trainer")  # 'admin', 'trainer', 'member'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    memberships_assigned = relationship("WorkoutAssignment", back_populates="assigned_by_user")

    @property
    def display_name(self):
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.full_name:
            return self.full_name
        return self.username


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    first_name = Column(String(50), nullable=False)
    last_name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False, index=True)
    gender = Column(String(10), default="male")  # 'male', 'female'
    job = Column(String(100), nullable=True)
    birth_date_shamsi = Column(String(10), nullable=True)
    height_cm = Column(Float, nullable=True)
    initial_weight_kg = Column(Float, nullable=True)
    photo_path = Column(String(255), nullable=True)
    
    registration_date_shamsi = Column(String(10), nullable=True)
    insurance_date_shamsi = Column(String(10), nullable=True)
    tuition_fee = Column(Float, nullable=True)
    
    membership_type = Column(String(50), default="12_sessions")
    # '8_sessions', '12_sessions', '16_sessions', '20_sessions', 'daily_access'
    
    membership_start_shamsi = Column(String(10), nullable=False)
    membership_expire_shamsi = Column(String(10), nullable=False)
    status = Column(String(20), default="active", index=True)  # 'active', 'expired', 'archived'
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    trainer = relationship("User", foreign_keys=[user_id])
    health_record = relationship("HealthRecord", back_populates="member", uselist=False, cascade="all, delete-orphan")
    assessments = relationship("PhysicalAssessment", back_populates="member", cascade="all, delete-orphan", order_by="PhysicalAssessment.assessment_date_shamsi.desc()")
    workout_assignments = relationship("WorkoutAssignment", back_populates="member", cascade="all, delete-orphan")
    nutrition_assignments = relationship("NutritionAssignment", back_populates="member", cascade="all, delete-orphan")
    medical_documents = relationship("MedicalDocument", back_populates="member", cascade="all, delete-orphan", order_by="MedicalDocument.created_at.desc()")

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def trainer_name(self):
        try:
            if self.trainer:
                return self.trainer.display_name
        except Exception:
            pass

        if self.user_id:
            try:
                from yalda.database.connection import get_session
                session = get_session()
                try:
                    user = session.query(User).get(self.user_id)
                    if user:
                        return user.display_name
                finally:
                    session.close()
            except Exception:
                pass
        return "عمومی / ادمین"



class HealthRecord(Base):
    __tablename__ = "health_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False, unique=True)
    
    has_hypertension = Column(Boolean, default=False)
    has_diabetes = Column(Boolean, default=False)
    has_heart_issue = Column(Boolean, default=False)
    other_medical = Column(Text, nullable=True)

    knee_injury = Column(Text, nullable=True)
    back_injury = Column(Text, nullable=True)
    shoulder_injury = Column(Text, nullable=True)
    wrist_injury = Column(Text, nullable=True)
    other_injuries = Column(Text, nullable=True)

    exercise_limitations = Column(Text, nullable=True)
    trainer_notes = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    member = relationship("Member", back_populates="health_record")

class MedicalDocument(Base):
    __tablename__ = "medical_documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    title = Column(String(150), nullable=False)
    file_path = Column(Text, nullable=False)
    created_at_shamsi = Column(String(10), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="medical_documents")

    @property
    def file_paths_list(self):
        if not self.file_path:
            return []
        return [p.strip() for p in self.file_path.split("||") if p.strip()]

class PhysicalAssessment(Base):
    __tablename__ = "physical_assessments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    assessment_date_shamsi = Column(String(10), nullable=False)
    
    height_cm = Column(Float, nullable=True)
    weight_kg = Column(Float, nullable=False)
    body_fat_percentage = Column(Float, nullable=True)
    bmi = Column(Float, nullable=True)
    
    arm_circ = Column(Float, nullable=True)
    chest_circ = Column(Float, nullable=True)
    waist_circ = Column(Float, nullable=True)
    thigh_circ = Column(Float, nullable=True)
    neck_circ = Column(Float, nullable=True)
    abdomen_circ = Column(Float, nullable=True)
    hip_circ = Column(Float, nullable=True)
    
    before_photo_path = Column(String(255), nullable=True)
    after_photo_path = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    member = relationship("Member", back_populates="assessments")

class Exercise(Base):
    __tablename__ = "exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_fa = Column(String(100), nullable=False, index=True)
    name_en = Column(String(100), nullable=True)
    primary_muscle = Column(String(50), nullable=False, index=True)  # 'chest', 'back', 'legs', 'shoulders', 'arms', 'abs'
    secondary_muscles = Column(String(100), nullable=True)
    equipment = Column(String(50), nullable=True)  # 'barbell', 'dumbbell', 'machine', 'bodyweight', 'cable'
    media_path = Column(String(255), nullable=True)
    media_type = Column(String(20), default="image")  # 'image', 'video', 'url'
    video_url = Column(String(500), nullable=True)  # URL to online video tutorial
    contraindications = Column(Text, nullable=True)  # e.g. 'back_injury', 'knee_injury'
    description = Column(Text, nullable=True)

class WorkoutPlan(Base):
    __tablename__ = "workout_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    goal = Column(String(50), nullable=False)  # 'fat_loss', 'hypertrophy', 'strength', 'general_fitness', 'endurance'
    days_per_week = Column(Integer, nullable=False, default=3)  # 2, 3, 4, 5, 6
    training_level = Column(String(50), default="beginner")  # 'beginner', 'intermediate', 'advanced'
    target_muscle_groups = Column(String(255), nullable=True)
    duration_weeks = Column(Integer, default=4)
    notes = Column(Text, nullable=True)
    version = Column(Integer, default=1)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    days = relationship("WorkoutDay", back_populates="plan", cascade="all, delete-orphan", order_by="WorkoutDay.day_number")
    assignments = relationship("WorkoutAssignment", back_populates="plan", cascade="all, delete-orphan")

class WorkoutDay(Base):
    __tablename__ = "workout_days"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=False)
    day_number = Column(Integer, nullable=False)
    day_title = Column(String(100), nullable=False)  # e.g. "روز اول: پا و شکم"

    plan = relationship("WorkoutPlan", back_populates="days")
    workout_exercises = relationship("WorkoutExercise", back_populates="day", cascade="all, delete-orphan", order_by="WorkoutExercise.order_index")

class WorkoutExercise(Base):
    __tablename__ = "workout_exercises"

    id = Column(Integer, primary_key=True, autoincrement=True)
    day_id = Column(Integer, ForeignKey("workout_days.id"), nullable=False)
    exercise_id = Column(Integer, ForeignKey("exercises.id"), nullable=False)
    
    sets = Column(Integer, default=3)
    reps = Column(String(50), default="10-12")
    weight_suggestion = Column(String(50), nullable=True)
    rest_seconds = Column(Integer, default=60)
    tempo = Column(String(20), nullable=True)  # e.g. "2-0-2-0"
    order_index = Column(Integer, default=1)
    trainer_notes = Column(Text, nullable=True)

    day = relationship("WorkoutDay", back_populates="workout_exercises")
    exercise = relationship("Exercise")

class WorkoutAssignment(Base):
    __tablename__ = "workout_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("workout_plans.id"), nullable=False)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_date_shamsi = Column(String(10), nullable=False)
    start_date_shamsi = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    member = relationship("Member", back_populates="workout_assignments")
    plan = relationship("WorkoutPlan", back_populates="assignments")
    assigned_by_user = relationship("User", back_populates="memberships_assigned")

class FoodItem(Base):
    __tablename__ = "food_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name_fa = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False)  # 'rice', 'bread', 'meat', 'dairy', 'legumes', 'fruits', 'vegetables'
    unit = Column(String(30), default="100 گرم")
    calories = Column(Float, nullable=False, default=0.0)
    protein_g = Column(Float, nullable=False, default=0.0)
    carbs_g = Column(Float, nullable=False, default=0.0)
    fat_g = Column(Float, nullable=False, default=0.0)
    is_custom = Column(Boolean, default=False)

class NutritionPlan(Base):
    __tablename__ = "nutrition_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(100), nullable=False)
    goal = Column(String(50), nullable=False)  # 'weight_loss', 'weight_gain', 'muscle_gain', 'maintenance'
    target_calories = Column(Float, nullable=False, default=2000.0)
    target_protein = Column(Float, nullable=False, default=150.0)
    target_carbs = Column(Float, nullable=False, default=200.0)
    target_fat = Column(Float, nullable=False, default=60.0)
    notes = Column(Text, nullable=True)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    meals = relationship("MealPlan", back_populates="plan", cascade="all, delete-orphan", order_by="MealPlan.order_index")
    assignments = relationship("NutritionAssignment", back_populates="plan", cascade="all, delete-orphan")

class MealPlan(Base):
    __tablename__ = "meal_plans"

    id = Column(Integer, primary_key=True, autoincrement=True)
    plan_id = Column(Integer, ForeignKey("nutrition_plans.id"), nullable=False)
    meal_name = Column(String(50), nullable=False)  # 'breakfast', 'morning_snack', 'lunch', 'afternoon_snack', 'dinner', 'evening_snack'
    order_index = Column(Integer, default=1)

    plan = relationship("NutritionPlan", back_populates="meals")
    items = relationship("MealItem", back_populates="meal", cascade="all, delete-orphan")

class MealItem(Base):
    __tablename__ = "meal_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    meal_id = Column(Integer, ForeignKey("meal_plans.id"), nullable=False)
    food_id = Column(Integer, ForeignKey("food_items.id"), nullable=False)
    amount = Column(Float, nullable=False, default=1.0)
    unit = Column(String(30), nullable=True)
    notes = Column(Text, nullable=True)

    meal = relationship("MealPlan", back_populates="items")
    food = relationship("FoodItem")

class NutritionAssignment(Base):
    __tablename__ = "nutrition_assignments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    plan_id = Column(Integer, ForeignKey("nutrition_plans.id"), nullable=False)
    assigned_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    assigned_date_shamsi = Column(String(10), nullable=False)
    start_date_shamsi = Column(String(10), nullable=False)
    is_active = Column(Boolean, default=True)
    notes = Column(Text, nullable=True)

    member = relationship("Member", back_populates="nutrition_assignments")
    plan = relationship("NutritionPlan", back_populates="assignments")

class BackupRecord(Base):
    __tablename__ = "backup_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    file_name = Column(String(100), nullable=False)
    file_path = Column(String(255), nullable=False)
    backup_date_shamsi = Column(String(10), nullable=False)
    backup_size_mb = Column(Float, default=0.0)
    created_at = Column(DateTime, default=datetime.utcnow)
