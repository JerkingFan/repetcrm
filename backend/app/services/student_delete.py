"""Hard-delete a student and all dependent rows in a safe order."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import (
    Homework,
    HomeworkSubmission,
    HomeworkTemplate,
    Lesson,
    LessonPackage,
    LessonRescheduleRequest,
    LessonSeries,
    PaymentIntent,
    PaymentReceipt,
    PaymentTransaction,
    Student,
    StudentDailyChallenge,
    TrialBooking,
)


def delete_student_cascade(db: Session, student: Student) -> None:
    """Remove student and related data. Does not commit."""
    sid = student.id

    lesson_ids = [
        row[0] for row in db.query(Lesson.id).filter(Lesson.student_id == sid).all()
    ]

    if lesson_ids:
        # Break self-FK among lessons before delete
        db.query(Lesson).filter(Lesson.rescheduled_from_lesson_id.in_(lesson_ids)).update(
            {Lesson.rescheduled_from_lesson_id: None},
            synchronize_session=False,
        )
        db.query(HomeworkTemplate).filter(HomeworkTemplate.source_lesson_id.in_(lesson_ids)).update(
            {HomeworkTemplate.source_lesson_id: None},
            synchronize_session=False,
        )
        # Detach package/series FKs so those parents can be removed freely
        db.query(Lesson).filter(Lesson.id.in_(lesson_ids)).update(
            {Lesson.package_id: None, Lesson.series_id: None},
            synchronize_session=False,
        )

        # Reschedule rows (also cascade via lesson, but be explicit)
        db.query(LessonRescheduleRequest).filter(
            LessonRescheduleRequest.student_id == sid
        ).delete(synchronize_session=False)

        # Submissions reference both homework and student
        db.query(HomeworkSubmission).filter(HomeworkSubmission.student_id == sid).delete(
            synchronize_session=False
        )

        hw_ids = [
            row[0]
            for row in db.query(Homework.id).filter(Homework.lesson_id.in_(lesson_ids)).all()
        ]
        if hw_ids:
            db.query(HomeworkSubmission).filter(HomeworkSubmission.homework_id.in_(hw_ids)).delete(
                synchronize_session=False
            )
            db.query(Homework).filter(Homework.id.in_(hw_ids)).delete(synchronize_session=False)

        # Checklist + lessons (checklist FK may lack ON DELETE CASCADE in legacy DBs)
        from app.models import ChecklistItem

        db.query(ChecklistItem).filter(ChecklistItem.lesson_id.in_(lesson_ids)).delete(
            synchronize_session=False
        )
        db.query(Lesson).filter(Lesson.id.in_(lesson_ids)).delete(synchronize_session=False)

    # Remaining student-scoped tables (idempotent if already empty)
    db.query(LessonRescheduleRequest).filter(LessonRescheduleRequest.student_id == sid).delete(
        synchronize_session=False
    )
    db.query(HomeworkSubmission).filter(HomeworkSubmission.student_id == sid).delete(
        synchronize_session=False
    )
    db.query(StudentDailyChallenge).filter(StudentDailyChallenge.student_id == sid).delete(
        synchronize_session=False
    )
    db.query(PaymentReceipt).filter(PaymentReceipt.student_id == sid).delete(
        synchronize_session=False
    )
    db.query(PaymentTransaction).filter(PaymentTransaction.student_id == sid).delete(
        synchronize_session=False
    )
    db.query(PaymentIntent).filter(PaymentIntent.student_id == sid).delete(
        synchronize_session=False
    )
    db.query(TrialBooking).filter(TrialBooking.student_id == sid).delete(
        synchronize_session=False
    )
    db.query(LessonPackage).filter(LessonPackage.student_id == sid).delete(
        synchronize_session=False
    )
    db.query(LessonSeries).filter(LessonSeries.student_id == sid).delete(
        synchronize_session=False
    )

    db.delete(student)
