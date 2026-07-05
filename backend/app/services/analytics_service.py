"""Business analytics: revenue, trial conversion, churn."""

from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import and_, case, func
from sqlalchemy.orm import Session

from app.models import Lesson, Student
from app.schemas import (
    AnalyticsChurnOut,
    AnalyticsOverview,
    AnalyticsRevenueMonth,
    AnalyticsTrialConversion,
)

CHURN_INACTIVE_DAYS = 30
TRIAL_WINDOW_DAYS = 90


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def build_analytics_overview(db: Session, tutor_id: int) -> AnalyticsOverview:
    today = date.today()
    horizon_start = today - timedelta(days=365)

    revenue_rows = (
        db.query(
            func.strftime("%Y-%m", Lesson.lesson_date).label("month"),
            func.coalesce(func.sum(Lesson.payment_amount), 0.0).label("amount"),
            func.count(Lesson.id).label("cnt"),
        )
        .filter(
            Lesson.tutor_id == tutor_id,
            Lesson.is_paid.is_(True),
            Lesson.lesson_date >= horizon_start,
        )
        .group_by("month")
        .order_by("month")
        .all()
    )
    revenue_by_month = [
        AnalyticsRevenueMonth(
            month=str(row.month),
            revenue=float(row.amount or 0),
            paid_lessons=int(row.cnt or 0),
        )
        for row in revenue_rows
    ]

    trial_cutoff = today - timedelta(days=TRIAL_WINDOW_DAYS)
    conducted_sq = (
        db.query(
            Lesson.student_id.label("student_id"),
            func.count(Lesson.id).label("conducted_count"),
            func.min(Lesson.lesson_date).label("first_date"),
        )
        .filter(
            Lesson.tutor_id == tutor_id,
            Lesson.is_conducted.is_(True),
        )
        .group_by(Lesson.student_id)
        .subquery()
    )
    trial_stats = (
        db.query(
            func.count(case((conducted_sq.c.conducted_count == 1, conducted_sq.c.student_id))).label(
                "trial_only"
            ),
            func.count(case((conducted_sq.c.conducted_count >= 2, conducted_sq.c.student_id))).label(
                "converted"
            ),
            func.count(conducted_sq.c.student_id).label("with_lessons"),
        )
        .filter(conducted_sq.c.first_date >= trial_cutoff)
        .one()
    )
    trial_only = int(trial_stats.trial_only or 0)
    converted = int(trial_stats.converted or 0)
    with_lessons = int(trial_stats.with_lessons or 0)
    conversion_rate = round((converted / with_lessons * 100) if with_lessons else 0.0, 1)

    trial_conversion = AnalyticsTrialConversion(
        period_days=TRIAL_WINDOW_DAYS,
        students_with_trial_lesson=trial_only,
        students_converted=converted,
        students_with_any_lesson=with_lessons,
        conversion_rate_percent=conversion_rate,
    )

    inactive_cutoff = today - timedelta(days=CHURN_INACTIVE_DAYS)
    active_recent = (
        db.query(func.count(func.distinct(Lesson.student_id)))
        .filter(
            Lesson.tutor_id == tutor_id,
            Lesson.lesson_date >= today - timedelta(days=90),
        )
        .scalar()
        or 0
    )
    churned = (
        db.query(func.count(Student.id))
        .filter(
            Student.tutor_id == tutor_id,
            Student.last_lesson_at.isnot(None),
            Student.last_lesson_at < inactive_cutoff,
        )
        .scalar()
        or 0
    )
    at_risk = (
        db.query(func.count(Student.id))
        .filter(
            Student.tutor_id == tutor_id,
            Student.last_lesson_at.isnot(None),
            Student.last_lesson_at >= inactive_cutoff,
            Student.last_lesson_at < today - timedelta(days=14),
        )
        .scalar()
        or 0
    )
    churn_rate = round((churned / active_recent * 100) if active_recent else 0.0, 1)

    churn = AnalyticsChurnOut(
        inactive_days_threshold=CHURN_INACTIVE_DAYS,
        churned_students=int(churned),
        at_risk_students=int(at_risk),
        active_last_90_days=int(active_recent),
        churn_rate_percent=churn_rate,
    )

    return AnalyticsOverview(
        revenue_by_month=revenue_by_month,
        trial_conversion=trial_conversion,
        churn=churn,
    )
