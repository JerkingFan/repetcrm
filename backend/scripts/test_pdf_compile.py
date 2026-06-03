from datetime import date
import os
import tempfile

from app.services.latex_convert import build_print_tex_document
from app.services.latex_compile import compile_tex_to_pdf
from app.services.smart_homework import generate_smart_homework_latex

latex = generate_smart_homework_latex(
    "Test",
    "Math",
    [{"topic": "Тригонометрические неравенства", "understanding": 3, "difficulty": "medium"}],
)
built = build_print_tex_document(latex, date.today(), subject="Math", student_name="Test")
out = os.path.join(tempfile.gettempdir(), "repetcrm_test.pdf")
ok = compile_tex_to_pdf(built, out)
print("compile_ok", ok, "size", os.path.getsize(out) if ok and os.path.isfile(out) else 0)
