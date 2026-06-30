-- Индексы для /dashboard и /lessons (существующие инсталляции)
CREATE INDEX IF NOT EXISTS idx_lessons_tutor_date ON lessons(tutor_id, lesson_date);
CREATE INDEX IF NOT EXISTS idx_lessons_tutor_date_desc ON lessons(tutor_id, lesson_date DESC);
CREATE INDEX IF NOT EXISTS idx_lessons_tutor_paid ON lessons(tutor_id, is_paid);
