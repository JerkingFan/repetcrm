-- Миграция для старых SQLite-баз (идемпотентно: ошибки «duplicate column» можно игнорировать)

-- users
ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0;
ALTER TABLE users ADD COLUMN subjects TEXT DEFAULT '[]';
ALTER TABLE users ADD COLUMN grade_levels TEXT DEFAULT '[]';
ALTER TABLE users ADD COLUMN teaching_format VARCHAR(50) DEFAULT '';

-- students
ALTER TABLE students ADD COLUMN grade VARCHAR(50) DEFAULT '';
ALTER TABLE students ADD COLUMN school VARCHAR(255) DEFAULT '';
ALTER TABLE students ADD COLUMN parent_contact VARCHAR(255) DEFAULT '';
ALTER TABLE students ADD COLUMN notes TEXT DEFAULT '';

-- lessons
ALTER TABLE lessons ADD COLUMN lesson_time VARCHAR(5) DEFAULT '10:00';
ALTER TABLE lessons ADD COLUMN is_conducted BOOLEAN DEFAULT 0;
ALTER TABLE lessons ADD COLUMN homework_prefs TEXT DEFAULT '';
