from sqlalchemy.orm import selectinload
from yalda.database.connection import get_session, mark_data_changed
from yalda.models.database_models import (
    Exercise, WorkoutPlan, WorkoutDay, WorkoutExercise, WorkoutAssignment, HealthRecord
)
from yalda.utils.jalali_date import get_today_shamsi

class WorkoutService:
    @staticmethod
    def get_all_exercises(muscle_group: str = None, equipment: str = None, search_query: str = None):
        session = get_session()
        try:
            query = session.query(Exercise)
            if muscle_group and muscle_group != "all":
                query = query.filter(Exercise.primary_muscle == muscle_group)
            if equipment and equipment != "all":
                query = query.filter(Exercise.equipment == equipment)
            if search_query:
                pattern = f"%{search_query.strip()}%"
                query = query.filter(Exercise.name_fa.like(pattern))
            return query.order_by(Exercise.name_fa).all()
        finally:
            session.close()

    @staticmethod
    def create_exercise(data: dict) -> Exercise:
        session = get_session()
        try:
            ex = Exercise(
                name_fa=data.get("name_fa"),
                name_en=data.get("name_en"),
                primary_muscle=data.get("primary_muscle"),
                secondary_muscles=data.get("secondary_muscles"),
                equipment=data.get("equipment"),
                media_path=data.get("media_path"),
                media_type=data.get("media_type", "image"),
                video_url=data.get("video_url"),
                contraindications=data.get("contraindications"),
                description=data.get("description")
            )
            session.add(ex)
            session.commit()
            mark_data_changed()
            return ex
        finally:
            session.close()

    @staticmethod
    def update_exercise(exercise_id: int, data: dict) -> Exercise:
        session = get_session()
        try:
            ex = session.query(Exercise).filter(Exercise.id == exercise_id).first()
            if not ex:
                raise ValueError("حرکت ورزشی یافت نشد.")
            for key, val in data.items():
                if hasattr(ex, key):
                    setattr(ex, key, val)
            session.commit()
            mark_data_changed()
            return ex
        finally:
            session.close()

    @staticmethod
    def get_all_plans():
        session = get_session()
        try:
            return session.query(WorkoutPlan)\
                .options(
                    selectinload(WorkoutPlan.days).selectinload(WorkoutDay.workout_exercises).selectinload(WorkoutExercise.exercise),
                    selectinload(WorkoutPlan.assignments)
                )\
                .order_by(WorkoutPlan.id.desc()).all()
        finally:
            session.close()

    @staticmethod
    def get_plan_by_id(plan_id: int):
        session = get_session()
        try:
            return session.query(WorkoutPlan)\
                .options(
                    selectinload(WorkoutPlan.days).selectinload(WorkoutDay.workout_exercises).selectinload(WorkoutExercise.exercise),
                    selectinload(WorkoutPlan.assignments)
                )\
                .filter(WorkoutPlan.id == plan_id).first()
        finally:
            session.close()


    @staticmethod
    def create_workout_plan(plan_data: dict, days_data: list) -> WorkoutPlan:
        """
        days_data format:
        [
            {
                "day_number": 1,
                "day_title": "روز اول: پا و شکم",
                "exercises": [
                    {"exercise_id": 1, "sets": 3, "reps": "10-12", "weight_suggestion": "50kg", "rest_seconds": 60, "tempo": "2-0-2-0", "trainer_notes": ""}
                ]
            }
        ]
        """
        session = get_session()
        try:
            plan = WorkoutPlan(
                title=plan_data.get("title"),
                goal=plan_data.get("goal"),
                days_per_week=int(plan_data.get("days_per_week", 3)),
                training_level=plan_data.get("training_level", "beginner"),
                target_muscle_groups=plan_data.get("target_muscle_groups"),
                duration_weeks=int(plan_data.get("duration_weeks", 4)),
                notes=plan_data.get("notes"),
                created_by_user_id=plan_data.get("created_by_user_id")
            )
            session.add(plan)
            session.flush()

            for day_info in days_data:
                w_day = WorkoutDay(
                    plan_id=plan.id,
                    day_number=day_info.get("day_number"),
                    day_title=day_info.get("day_title")
                )
                session.add(w_day)
                session.flush()

                for idx, ex_info in enumerate(day_info.get("exercises", []), start=1):
                    ex_id = ex_info.get("exercise_id")
                    if not ex_id:
                        continue
                    w_ex = WorkoutExercise(
                        day_id=w_day.id,
                        exercise_id=ex_id,
                        sets=int(ex_info.get("sets", 3)),
                        reps=str(ex_info.get("reps", "10")),
                        weight_suggestion=ex_info.get("weight_suggestion"),
                        rest_seconds=int(ex_info.get("rest_seconds", 60)),
                        tempo=ex_info.get("tempo"),
                        order_index=idx,
                        trainer_notes=ex_info.get("trainer_notes")
                    )
                    session.add(w_ex)

            session.commit()
            mark_data_changed()
            return plan
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def get_relevant_plans_for_member(member_id: int):
        """
        Returns relevant workout plans filtered/scored based on member's health limitations & goals.
        """
        session = get_session()
        try:
            health_rec = session.query(HealthRecord).filter(HealthRecord.member_id == member_id).first()
            limitations = []
            if health_rec:
                if health_rec.knee_injury: limitations.append("knee_injury")
                if health_rec.back_injury: limitations.append("back_injury")
                if health_rec.shoulder_injury: limitations.append("shoulder_injury")
                if health_rec.wrist_injury: limitations.append("wrist_injury")

            all_plans = session.query(WorkoutPlan).all()
            scored_plans = []

            for p in all_plans:
                warnings = []
                # Inspect plan exercises for contraindications
                for day in p.days:
                    for we in day.workout_exercises:
                        if we.exercise and we.exercise.contraindications:
                            for lim in limitations:
                                if lim in we.exercise.contraindications:
                                    warnings.append(f"حرکت '{we.exercise.name_fa}' با {lim.replace('_', ' ')} ناهمخوان است.")
                
                scored_plans.append({
                    "plan": p,
                    "warnings": list(set(warnings)),
                    "is_safe": len(warnings) == 0
                })
            return scored_plans
        finally:
            session.close()

    @staticmethod
    def assign_plan_to_member(member_id: int, plan_id: int, user_id: int = None, notes: str = None):
        session = get_session()
        try:
            # Deactivate previous assignments
            session.query(WorkoutAssignment).filter(
                WorkoutAssignment.member_id == member_id,
                WorkoutAssignment.is_active == True
            ).update({"is_active": False})

            today_str = get_today_shamsi()
            assignment = WorkoutAssignment(
                member_id=member_id,
                plan_id=plan_id,
                assigned_by_user_id=user_id,
                assigned_date_shamsi=today_str,
                start_date_shamsi=today_str,
                is_active=True,
                notes=notes
            )
            session.add(assignment)
            session.commit()
            mark_data_changed()
            return assignment
        finally:
            session.close()

    @staticmethod
    def get_active_assignment(member_id: int):
        session = get_session()
        try:
            return session.query(WorkoutAssignment)\
                .options(selectinload(WorkoutAssignment.plan).selectinload(WorkoutPlan.days).selectinload(WorkoutDay.workout_exercises).selectinload(WorkoutExercise.exercise))\
                .filter(WorkoutAssignment.member_id == member_id, WorkoutAssignment.is_active == True)\
                .first()
        finally:
            session.close()

    @staticmethod
    def get_member_assignments(member_id: int):
        session = get_session()
        try:
            return session.query(WorkoutAssignment)\
                .options(selectinload(WorkoutAssignment.plan).selectinload(WorkoutPlan.days).selectinload(WorkoutDay.workout_exercises).selectinload(WorkoutExercise.exercise))\
                .filter(WorkoutAssignment.member_id == member_id)\
                .order_by(WorkoutAssignment.id.desc())\
                .all()
        finally:
            session.close()

    @staticmethod
    def delete_exercise(exercise_id: int):
        session = get_session()
        try:
            ex = session.query(Exercise).filter(Exercise.id == exercise_id).first()
            if ex:
                session.delete(ex)
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
    def delete_workout_assignment(assignment_id: int):
        session = get_session()
        try:
            asgn = session.query(WorkoutAssignment).filter(WorkoutAssignment.id == assignment_id).first()
            if asgn:
                plan_id = asgn.plan_id
                session.delete(asgn)
                session.flush()

                # Check if this plan is used in any remaining assignments
                remaining = session.query(WorkoutAssignment).filter(WorkoutAssignment.plan_id == plan_id).count()
                if remaining == 0:
                    orphan_plan = session.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
                    if orphan_plan:
                        session.delete(orphan_plan)

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
    def update_workout_plan(plan_id: int, plan_data: dict, days_data: list) -> WorkoutPlan:
        session = get_session()
        try:
            plan = session.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
            if not plan:
                raise ValueError("برنامه تمرینی یافت نشد.")

            for key, val in plan_data.items():
                if hasattr(plan, key) and val is not None:
                    setattr(plan, key, val)

            # Clear existing days & exercises cleanly
            day_ids = [d[0] for d in session.query(WorkoutDay.id).filter(WorkoutDay.plan_id == plan.id).all()]
            if day_ids:
                session.query(WorkoutExercise).filter(WorkoutExercise.day_id.in_(day_ids)).delete(synchronize_session=False)
            session.query(WorkoutDay).filter(WorkoutDay.plan_id == plan.id).delete(synchronize_session=False)
            session.flush()

            for day_info in days_data:
                w_day = WorkoutDay(
                    plan_id=plan.id,
                    day_number=day_info.get("day_number"),
                    day_title=day_info.get("day_title")
                )
                session.add(w_day)
                session.flush()

                for idx, ex_info in enumerate(day_info.get("exercises", []), start=1):
                    ex_id = ex_info.get("exercise_id")
                    if not ex_id:
                        continue
                    w_ex = WorkoutExercise(
                        day_id=w_day.id,
                        exercise_id=ex_id,
                        sets=int(ex_info.get("sets", 3)),
                        reps=str(ex_info.get("reps", "10")),
                        weight_suggestion=ex_info.get("weight_suggestion"),
                        rest_seconds=int(ex_info.get("rest_seconds", 60)),
                        tempo=ex_info.get("tempo"),
                        order_index=idx,
                        trainer_notes=ex_info.get("trainer_notes")
                    )
                    session.add(w_ex)

            session.commit()
            mark_data_changed()
            return plan
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def delete_plan(plan_id: int):
        session = get_session()
        try:
            plan = session.query(WorkoutPlan).filter(WorkoutPlan.id == plan_id).first()
            if plan:
                # Delete any assignments first
                session.query(WorkoutAssignment).filter(WorkoutAssignment.plan_id == plan.id).delete()
                # Delete plan (SQLAlchemy cascade deletes days and exercises)
                session.delete(plan)
                session.commit()
                mark_data_changed()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
