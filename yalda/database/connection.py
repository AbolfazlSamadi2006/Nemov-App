from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session
import config
from yalda.models.database_models import Base

engine = create_engine(config.DATABASE_URI, echo=False, connect_args={"check_same_thread": False})
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False))

_session_has_changes = False

def mark_data_changed():
    global _session_has_changes
    _session_has_changes = True

def reset_data_changed():
    global _session_has_changes
    _session_has_changes = False

def has_data_changed() -> bool:
    return _session_has_changes

def get_session():
    """Returns a new SQLAlchemy session."""
    return SessionLocal()

def check_and_migrate_db():
    """Checks and migrates new columns for existing SQLite database files."""
    from sqlalchemy import inspect, text
    inspector = inspect(engine)
    if "members" in inspector.get_table_names():
        columns = [c["name"] for c in inspector.get_columns("members")]
        with engine.connect() as conn:
            if "registration_date_shamsi" not in columns:
                conn.execute(text("ALTER TABLE members ADD COLUMN registration_date_shamsi VARCHAR(10);"))
            if "insurance_date_shamsi" not in columns:
                conn.execute(text("ALTER TABLE members ADD COLUMN insurance_date_shamsi VARCHAR(10);"))
            if "tuition_fee" not in columns:
                conn.execute(text("ALTER TABLE members ADD COLUMN tuition_fee FLOAT;"))
            if "job" not in columns:
                conn.execute(text("ALTER TABLE members ADD COLUMN job VARCHAR(100);"))
            if "activity_level" not in columns:
                conn.execute(text("ALTER TABLE members ADD COLUMN activity_level VARCHAR(30) DEFAULT 'moderately_active';"))
            conn.commit()

    if "physical_assessments" in inspector.get_table_names():
        pa_columns = [c["name"] for c in inspector.get_columns("physical_assessments")]
        with engine.connect() as conn:
            if "height_cm" not in pa_columns:
                conn.execute(text("ALTER TABLE physical_assessments ADD COLUMN height_cm FLOAT;"))
            if "neck_circ" not in pa_columns:
                conn.execute(text("ALTER TABLE physical_assessments ADD COLUMN neck_circ FLOAT;"))
            if "abdomen_circ" not in pa_columns:
                conn.execute(text("ALTER TABLE physical_assessments ADD COLUMN abdomen_circ FLOAT;"))
            if "hip_circ" not in pa_columns:
                conn.execute(text("ALTER TABLE physical_assessments ADD COLUMN hip_circ FLOAT;"))
            if "bmr" not in pa_columns:
                conn.execute(text("ALTER TABLE physical_assessments ADD COLUMN bmr FLOAT;"))
            if "tdee" not in pa_columns:
                conn.execute(text("ALTER TABLE physical_assessments ADD COLUMN tdee FLOAT;"))
            conn.commit()

    if "users" in inspector.get_table_names():
        u_columns = [c["name"] for c in inspector.get_columns("users")]
        with engine.connect() as conn:
            if "first_name" not in u_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN first_name VARCHAR(50);"))
            if "last_name" not in u_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN last_name VARCHAR(50);"))
            if "phone" not in u_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN phone VARCHAR(20);"))
            if "birth_date_shamsi" not in u_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN birth_date_shamsi VARCHAR(10);"))
            if "photo_path" not in u_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN photo_path VARCHAR(255);"))
            if "recovery_code" not in u_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN recovery_code VARCHAR(100);"))
            if "email" not in u_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN email VARCHAR(120);"))
            if "plain_password" not in u_columns:
                conn.execute(text("ALTER TABLE users ADD COLUMN plain_password VARCHAR(100);"))
            conn.commit()

    if "exercises" in inspector.get_table_names():
        ex_columns = [c["name"] for c in inspector.get_columns("exercises")]
        with engine.connect() as conn:
            if "video_url" not in ex_columns:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN video_url VARCHAR(500);"))
            if "is_corrective" not in ex_columns:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN is_corrective BOOLEAN DEFAULT 0;"))
            if "thumbnail_path" not in ex_columns:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN thumbnail_path VARCHAR(500);"))
            if "video_cloud_url" not in ex_columns:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN video_cloud_url VARCHAR(500);"))
            if "is_custom" not in ex_columns:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN is_custom BOOLEAN DEFAULT 0;"))
            if "is_unlisted" not in ex_columns:
                conn.execute(text("ALTER TABLE exercises ADD COLUMN is_unlisted BOOLEAN DEFAULT 0;"))
            conn.commit()

    if "food_items" in inspector.get_table_names():
        fi_columns = [c["name"] for c in inspector.get_columns("food_items")]
        with engine.connect() as conn:
            if "is_unlisted" not in fi_columns:
                conn.execute(text("ALTER TABLE food_items ADD COLUMN is_unlisted BOOLEAN DEFAULT 0;"))
            conn.commit()

    if "workout_exercises" in inspector.get_table_names():
        we_columns = [c["name"] for c in inspector.get_columns("workout_exercises")]
        with engine.connect() as conn:
            if "custom_exercise_name" not in we_columns:
                conn.execute(text("ALTER TABLE workout_exercises ADD COLUMN custom_exercise_name VARCHAR(100);"))
            conn.commit()

    if "meal_items" in inspector.get_table_names():
        mi_columns = [c["name"] for c in inspector.get_columns("meal_items")]
        with engine.connect() as conn:
            if "custom_food_name" not in mi_columns:
                conn.execute(text("ALTER TABLE meal_items ADD COLUMN custom_food_name VARCHAR(100);"))
            conn.commit()

    if "members" in inspector.get_table_names():
        m_columns = [c["name"] for c in inspector.get_columns("members")]
        with engine.connect() as conn:
            if "export_folder_path" not in m_columns:
                conn.execute(text("ALTER TABLE members ADD COLUMN export_folder_path VARCHAR(500);"))
            conn.commit()

    # Automatically seed initial tuition records from existing members if empty
    if "tuition_payments" in inspector.get_table_names():
        from yalda.models.database_models import TuitionPayment, Member
        session = SessionLocal()
        try:
            if session.query(TuitionPayment).count() == 0:
                members_with_fee = session.query(Member).filter(Member.tuition_fee > 0).all()
                for m in members_with_fee:
                    pay_date = m.membership_start_shamsi or m.registration_date_shamsi or "1405/01/01"
                    tp = TuitionPayment(
                        member_id=m.id,
                        user_id=m.user_id,
                        amount=float(m.tuition_fee),
                        payment_date_shamsi=pay_date,
                        payment_type="شهریه دوره ماهانه",
                        notes="ثبت خودکار از سوابق عضو"
                    )
                    session.add(tp)
                session.commit()
        except Exception:
            session.rollback()
        finally:
            session.close()

    # Automatically migrate legacy workers.dev URLs in exercises table to official storage domain
    if "exercises" in inspector.get_table_names():
        target_domain = config.DEFAULT_CLOUD_BACKUP_URL.replace("https://", "").replace("http://", "").rstrip("/")
        with engine.connect() as conn:
            conn.execute(text(
                f"UPDATE exercises SET video_url = REPLACE(video_url, 'gymassistantbackup.a-samadi2006.workers.dev', '{target_domain}') "
                "WHERE video_url LIKE '%workers.dev%';"
            ))
            conn.execute(text(
                f"UPDATE exercises SET video_cloud_url = REPLACE(video_cloud_url, 'gymassistantbackup.a-samadi2006.workers.dev', '{target_domain}') "
                "WHERE video_cloud_url LIKE '%workers.dev%';"
            ))
            conn.execute(text(
                f"UPDATE exercises SET video_url = REPLACE(video_url, 'storage.gymassistantapp.ir', '{target_domain}') "
                "WHERE video_url LIKE '%storage.gymassistantapp.ir%';"
            ))
            conn.execute(text(
                f"UPDATE exercises SET video_cloud_url = REPLACE(video_cloud_url, 'storage.gymassistantapp.ir', '{target_domain}') "
                "WHERE video_cloud_url LIKE '%storage.gymassistantapp.ir%';"
            ))
            conn.commit()




def init_db():
    """Creates database tables and seeds initial default data if needed."""
    Base.metadata.create_all(bind=engine)
    check_and_migrate_db()
    
    # Import and run seed data initialization
    from yalda.database.seed_data import seed_initial_data
    session = SessionLocal()
    try:
        seed_initial_data(session)
    finally:
        session.close()
