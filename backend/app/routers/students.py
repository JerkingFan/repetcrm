from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Student, Lesson
from app.schemas import StudentCreate, StudentUpdate, StudentOut, StudentWithLessons, LessonOut

router = APIRouter(prefix="/students", tags=["students"])


def lesson_to_out(lesson) -> LessonOut:
    return LessonOut(
        id=lesson.id,
        student_id=lesson.student_id,
        lesson_date=lesson.lesson_date,
        duration_minutes=lesson.duration_minutes,
        payment_amount=lesson.payment_amount,
        is_paid=lesson.is_paid,
        notes=lesson.notes,
        created_at=lesson.created_at,
        student_name=lesson.student.name if lesson.student else None,
        checklist_items=lesson.checklist_items,
        homework=lesson.homework,
    )


@router.get("", response_model=list[StudentOut])
def list_students(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return db.query(Student).filter(Student.tutor_id == user.id).order_by(Student.name).all()


@router.post("", response_model=StudentOut, status_code=201)
def create_student(data: StudentCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = Student(tutor_id=user.id, **data.model_dump())
    db.add(student)
    db.commit()
    db.refresh(student)
    return student


@router.get("/{student_id}", response_model=StudentWithLessons)
def get_student(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = (
        db.query(Student)
        .options(
            joinedload(Student.lessons).joinedload(Lesson.checklist_items),
            joinedload(Student.lessons).joinedload(Lesson.homework),
        )
        .filter(Student.id == student_id, Student.tutor_id == user.id)
        .first()
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    lessons_out = [lesson_to_out(l) for l in sorted(student.lessons, key=lambda x: x.lesson_date, reverse=True)]
    return StudentWithLessons(
        id=student.id,
        name=student.name,
        subject=student.subject,
        contact=student.contact,
        created_at=student.created_at,
        lessons=lessons_out,
    )


@router.put("/{student_id}", response_model=StudentOut)
def update_student(
    student_id: int,
    data: StudentUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(student, k, v)
    db.commit()
    db.refresh(student)
    return student


@router.delete("/{student_id}", status_code=204)
def delete_student(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    student = db.query(Student).filter(Student.id == student_id, Student.tutor_id == user.id).first()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    db.delete(student)
    db.commit()
