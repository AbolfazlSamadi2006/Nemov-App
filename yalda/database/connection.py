from sqlalchemy import create_engine, event
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
    global _session_has_changes
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
