from fastapi.responses import JSONResponse

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User, Homework, Lesson
from pydantic import BaseModel

from app.schemas import HomeworkUpdate, HomeworkOut
from app.services.homework_output import homework_content_to_html
from app.services.latex_convert import (
    homework_html_to_python_script,
    latex_to_python_expression,
    process_homework_html,
)
from app.services.pdf import (
    homework_pdf_cache_fresh,
    homework_pdf_path,
    invalidate_homework_pdf,
)
from app.services.job_queue import job_queue, ARQ_TASK_BUILD_PDF
from app.services.job_tasks import run_build_pdf


router = APIRouter(prefix="/homework", tags=["homework"])


class LatexConvertIn(BaseModel):
    html: str


class LatexConvertOut(BaseModel):
    expressions: list[str]
    python_expressions: list[str]
    python_script: str
    html_rendered: str


def get_homework_or_404(homework_id: int, user: User, db: Session) -> Homework:
    hw = (
        db.query(Homework)
        .join(Lesson)
        .options(
            joinedload(Homework.lesson).joinedload(Lesson.student),
            joinedload(Homework.lesson).joinedload(Lesson.checklist_items),
        )
        .filter(Homework.id == homework_id, Lesson.tutor_id == user.id)
        .first()
    )
    if not hw:
        raise HTTPException(status_code=404, detail="Homework not found")
    return hw


@router.post("/latex/convert", response_model=LatexConvertOut)
def convert_latex(data: LatexConvertIn, _user: User = Depends(get_current_user)):
    """LaTeX в домашке -> Python-скрипт + HTML с формулами-картинками."""
    from app.services.latex_convert import extract_latex_expressions

    exprs = extract_latex_expressions(data.html)
    return LatexConvertOut(
        expressions=exprs,
        python_expressions=[latex_to_python_expression(e) for e in exprs],
        python_script=homework_html_to_python_script(data.html),
        html_rendered=homework_content_to_html(data.html),
    )


@router.get("/{homework_id}/latex")
def download_latex(
    homework_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hw = get_homework_or_404(homework_id, user, db)
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        hw.homework_text,
        media_type="application/x-tex",
        headers={
            "Content-Disposition": f'attachment; filename="homework_{homework_id}.tex"'
        },
    )


@router.get("/{homework_id}/python-script")
def download_python_script(
    homework_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hw = get_homework_or_404(homework_id, user, db)
    script = homework_html_to_python_script(hw.homework_text)
    from fastapi.responses import PlainTextResponse

    return PlainTextResponse(
        script,
        media_type="text/x-python",
        headers={
            "Content-Disposition": f'attachment; filename="homework_{homework_id}.py"'
        },
    )


@router.get("/{homework_id}/preview")
def preview_homework_html(
    homework_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from app.services.homework_output import needs_pdf_latex_rebuild
    from app.services.homework_prefs import apply_prefs_to_checklist, parse_homework_prefs
    from app.services.smart_homework import generate_smart_homework_latex

    hw = get_homework_or_404(homework_id, user, db)
    lesson = hw.lesson
    text = hw.homework_text
    prefs = parse_homework_prefs(lesson.homework_prefs)
    checklist = apply_prefs_to_checklist(
        [
            {
                "topic": i.topic,
                "work_type": i.work_type,
                "difficulty": i.difficulty,
                "understanding": i.understanding,
            }
            for i in lesson.checklist_items
        ],
        prefs,
    )
    if checklist and needs_pdf_latex_rebuild(text):
        text = generate_smart_homework_latex(
            lesson.student.name,
            lesson.student.subject,
            checklist,
            lesson.student.grade or "",
            homework_prefs=prefs,
        )
    return {"html": homework_content_to_html(text, render_math_images=True)}


@router.put("/{homework_id}", response_model=HomeworkOut)
def update_homework(
    homework_id: int,
    data: HomeworkUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    hw = get_homework_or_404(homework_id, user, db)
    hw.homework_text = data.homework_text
    db.commit()
    db.refresh(hw)
    invalidate_homework_pdf(hw.id)
    return HomeworkOut(
        id=hw.id,
        lesson_id=hw.lesson_id,
        homework_text=hw.homework_text,
        created_at=hw.created_at,
        updated_at=hw.updated_at,
        student_name=hw.lesson.student.name,
        lesson_date=hw.lesson.lesson_date,
    )


@router.get("/{homework_id}/pdf")
async def download_pdf(homework_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    hw = get_homework_or_404(homework_id, user, db)
    if not hw.homework_text.strip():
        raise HTTPException(status_code=400, detail="Домашнее задание пустое")
    lesson = hw.lesson
    from app.services.homework_prefs import apply_prefs_to_checklist, parse_homework_prefs

    prefs = parse_homework_prefs(lesson.homework_prefs)
    checklist = apply_prefs_to_checklist(
        [
            {
                "topic": i.topic,
                "work_type": i.work_type,
                "difficulty": i.difficulty,
                "understanding": i.understanding,
            }
            for i in lesson.checklist_items
        ],
        prefs,
    )
    cached = homework_pdf_path(hw.id)
    if homework_pdf_cache_fresh(cached, hw.updated_at):
        path = cached
    else:
        # Start background build and ask client to poll.
        job = await job_queue.enqueue_unique(
            owner_user_id=user.id,
            key_type="homework",
            key_value=homework_id,
            job_type="build_pdf",
            arq_task=ARQ_TASK_BUILD_PDF,
            arq_args=(homework_id, user.id),
            inprocess_runner=lambda: run_build_pdf(homework_id, user.id),
        )
        return JSONResponse(
            status_code=202,
            content={"job_id": job.id, "status": job.status},
            headers={"Retry-After": "2"},
        )
    filename = f"homework_{lesson.student.name}_{lesson.lesson_date}.pdf".replace(" ", "_")
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=filename,
        headers={"Access-Control-Expose-Headers": "Content-Disposition"},
    )
