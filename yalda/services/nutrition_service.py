from sqlalchemy.orm import selectinload
from yalda.database.connection import get_session, mark_data_changed
from yalda.models.database_models import (
    FoodItem, NutritionPlan, MealPlan, MealItem, NutritionAssignment
)
from yalda.utils.jalali_date import get_today_shamsi

class NutritionService:
    @staticmethod
    def get_all_foods(category: str = None, search_query: str = None):
        session = get_session()
        try:
            query = session.query(FoodItem)
            if category and category != "all":
                query = query.filter(FoodItem.category == category)
            if search_query:
                pattern = f"%{search_query.strip()}%"
                query = query.filter(FoodItem.name_fa.like(pattern))
            return query.order_by(FoodItem.name_fa).all()
        finally:
            session.close()

    @staticmethod
    def add_custom_food(data: dict) -> FoodItem:
        session = get_session()
        try:
            food = FoodItem(
                name_fa=data.get("name_fa"),
                category=data.get("category", "rice"),
                unit=data.get("unit", "100 گرم"),
                calories=float(data.get("calories", 0.0)),
                protein_g=float(data.get("protein_g", 0.0)),
                carbs_g=float(data.get("carbs_g", 0.0)),
                fat_g=float(data.get("fat_g", 0.0)),
                is_custom=True
            )
            session.add(food)
            session.commit()
            mark_data_changed()
            return food
        finally:
            session.close()

    @staticmethod
    def update_food(food_id: int, data: dict) -> FoodItem:
        session = get_session()
        try:
            food = session.query(FoodItem).filter(FoodItem.id == food_id).first()
            if not food:
                raise ValueError("ماده غذایی یافت نشد.")
            for key, val in data.items():
                if hasattr(food, key):
                    setattr(food, key, val)
            session.commit()
            mark_data_changed()
            return food
        finally:
            session.close()

    @staticmethod
    def get_all_plans():
        session = get_session()
        try:
            return session.query(NutritionPlan)\
                .options(
                    selectinload(NutritionPlan.meals).selectinload(MealPlan.items).selectinload(MealItem.food),
                    selectinload(NutritionPlan.assignments)
                )\
                .order_by(NutritionPlan.id.desc()).all()
        finally:
            session.close()

    @staticmethod
    def get_plan_by_id(plan_id: int):
        session = get_session()
        try:
            return session.query(NutritionPlan)\
                .options(
                    selectinload(NutritionPlan.meals).selectinload(MealPlan.items).selectinload(MealItem.food),
                    selectinload(NutritionPlan.assignments)
                )\
                .filter(NutritionPlan.id == plan_id).first()
        finally:
            session.close()

    @staticmethod
    def create_nutrition_plan(plan_data: dict, meals_data: list) -> NutritionPlan:
        """
        meals_data format:
        [
            {
                "meal_name": "breakfast",  # 'breakfast', 'morning_snack', 'lunch', 'afternoon_snack', 'dinner', 'evening_snack'
                "order_index": 1,
                "items": [
                    {"food_id": 1, "amount": 2.0, "unit": "100 گرم", "notes": "با نان سنگک"}
                ]
            }
        ]
        """
        session = get_session()
        try:
            plan = NutritionPlan(
                title=plan_data.get("title"),
                goal=plan_data.get("goal", "muscle_gain"),
                target_calories=float(plan_data.get("target_calories", 2000.0)),
                target_protein=float(plan_data.get("target_protein", 150.0)),
                target_carbs=float(plan_data.get("target_carbs", 200.0)),
                target_fat=float(plan_data.get("target_fat", 60.0)),
                notes=plan_data.get("notes"),
                created_by_user_id=plan_data.get("created_by_user_id")
            )
            session.add(plan)
            session.flush()

            for idx, m_info in enumerate(meals_data, start=1):
                meal = MealPlan(
                    plan_id=plan.id,
                    meal_name=m_info.get("meal_name"),
                    order_index=idx
                )
                session.add(meal)
                session.flush()

                for item_info in m_info.get("items", []):
                    f_id = item_info.get("food_id")
                    if not f_id:
                        continue
                    m_item = MealItem(
                        meal_id=meal.id,
                        food_id=f_id,
                        amount=float(item_info.get("amount", 1.0)),
                        unit=item_info.get("unit"),
                        notes=item_info.get("notes")
                    )
                    session.add(m_item)

            session.commit()
            mark_data_changed()
            return plan
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def assign_nutrition_plan(member_id: int, plan_id: int, user_id: int = None, notes: str = None):
        session = get_session()
        try:
            session.query(NutritionAssignment).filter(
                NutritionAssignment.member_id == member_id,
                NutritionAssignment.is_active == True
            ).update({"is_active": False})

            today_str = get_today_shamsi()
            assignment = NutritionAssignment(
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
            return session.query(NutritionAssignment)\
                .options(selectinload(NutritionAssignment.plan).selectinload(NutritionPlan.meals).selectinload(MealPlan.items).selectinload(MealItem.food))\
                .filter(NutritionAssignment.member_id == member_id, NutritionAssignment.is_active == True)\
                .first()
        finally:
            session.close()

    @staticmethod
    def get_member_assignments(member_id: int):
        session = get_session()
        try:
            return session.query(NutritionAssignment)\
                .options(selectinload(NutritionAssignment.plan).selectinload(NutritionPlan.meals).selectinload(MealPlan.items).selectinload(MealItem.food))\
                .filter(NutritionAssignment.member_id == member_id)\
                .order_by(NutritionAssignment.id.desc())\
                .all()
        finally:
            session.close()

    @staticmethod
    def delete_food(food_id: int):
        session = get_session()
        try:
            food = session.query(FoodItem).filter(FoodItem.id == food_id).first()
            if food:
                deleted_name = food.name_fa
                session.delete(food)
                session.flush()

                if deleted_name:
                    from yalda.utils.duplicate_helper import get_resequenced_names
                    remaining = session.query(FoodItem).all()
                    updates = get_resequenced_names(deleted_name, [(f, f.name_fa) for f in remaining])
                    for f_obj, new_name in updates:
                        f_obj.name_fa = new_name

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
    def delete_nutrition_assignment(assignment_id: int):
        session = get_session()
        try:
            asgn = session.query(NutritionAssignment).filter(NutritionAssignment.id == assignment_id).first()
            if asgn:
                plan_id = asgn.plan_id
                member_id = asgn.member_id
                deleted_title = asgn.plan.title if asgn.plan else ""
                session.delete(asgn)
                session.flush()

                # Check if this plan is used in any remaining assignments
                remaining = session.query(NutritionAssignment).filter(NutritionAssignment.plan_id == plan_id).count()
                if remaining == 0:
                    orphan_plan = session.query(NutritionPlan).filter(NutritionPlan.id == plan_id).first()
                    if orphan_plan:
                        session.delete(orphan_plan)
                        session.flush()

                if deleted_title and member_id:
                    from yalda.utils.duplicate_helper import get_resequenced_names
                    remaining_asgns = session.query(NutritionAssignment).filter(NutritionAssignment.member_id == member_id).all()
                    updates = get_resequenced_names(deleted_title, [(a.plan, a.plan.title) for a in remaining_asgns if a.plan and a.plan.title])
                    for p_obj, new_title in updates:
                        p_obj.title = new_title

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
    def update_nutrition_plan(plan_id: int, plan_data: dict, meals_data: list) -> NutritionPlan:
        session = get_session()
        try:
            plan = session.query(NutritionPlan).filter(NutritionPlan.id == plan_id).first()
            if not plan:
                raise ValueError("برنامه غذایی یافت نشد.")

            for key, val in plan_data.items():
                if hasattr(plan, key) and val is not None:
                    setattr(plan, key, val)

            # Clear existing meals & items cleanly
            meal_ids = [m[0] for m in session.query(MealPlan.id).filter(MealPlan.plan_id == plan.id).all()]
            if meal_ids:
                session.query(MealItem).filter(MealItem.meal_id.in_(meal_ids)).delete(synchronize_session=False)
            session.query(MealPlan).filter(MealPlan.plan_id == plan.id).delete(synchronize_session=False)
            session.flush()

            for idx, m_info in enumerate(meals_data, start=1):
                meal = MealPlan(
                    plan_id=plan.id,
                    meal_name=m_info.get("meal_name"),
                    order_index=idx
                )
                session.add(meal)
                session.flush()

                for item_info in m_info.get("items", []):
                    f_id = item_info.get("food_id")
                    if not f_id:
                        continue
                    m_item = MealItem(
                        meal_id=meal.id,
                        food_id=f_id,
                        amount=float(item_info.get("amount", 1.0)),
                        unit=item_info.get("unit"),
                        notes=item_info.get("notes")
                    )
                    session.add(m_item)

            session.commit()
            mark_data_changed()
            return plan
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    @staticmethod
    def delete_nutrition_plan(plan_id: int):
        session = get_session()
        try:
            plan = session.query(NutritionPlan).filter(NutritionPlan.id == plan_id).first()
            if plan:
                deleted_title = plan.title
                # Delete any assignments first
                session.query(NutritionAssignment).filter(NutritionAssignment.plan_id == plan.id).delete()
                # Delete plan (SQLAlchemy cascade deletes meals and meal items)
                session.delete(plan)
                session.flush()

                if deleted_title:
                    from yalda.utils.duplicate_helper import get_resequenced_names
                    remaining = session.query(NutritionPlan).all()
                    updates = get_resequenced_names(deleted_title, [(p, p.title) for p in remaining])
                    for p_obj, new_title in updates:
                        p_obj.title = new_title

                session.commit()
                mark_data_changed()
                return True
            return False
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()
