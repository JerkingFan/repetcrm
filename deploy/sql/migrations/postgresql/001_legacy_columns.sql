-- Миграция для БД, созданных до полной схемы (PostgreSQL)
-- Безопасно запускать повторно: ADD COLUMN IF NOT EXISTS (PG 11+ через DO block)

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'onboarding_completed') THEN
        ALTER TABLE users ADD COLUMN onboarding_completed BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'subjects') THEN
        ALTER TABLE users ADD COLUMN subjects TEXT NOT NULL DEFAULT '[]';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'grade_levels') THEN
        ALTER TABLE users ADD COLUMN grade_levels TEXT NOT NULL DEFAULT '[]';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'users' AND column_name = 'teaching_format') THEN
        ALTER TABLE users ADD COLUMN teaching_format VARCHAR(50) NOT NULL DEFAULT '';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'students' AND column_name = 'grade') THEN
        ALTER TABLE students ADD COLUMN grade VARCHAR(50) NOT NULL DEFAULT '';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'students' AND column_name = 'school') THEN
        ALTER TABLE students ADD COLUMN school VARCHAR(255) NOT NULL DEFAULT '';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'students' AND column_name = 'parent_contact') THEN
        ALTER TABLE students ADD COLUMN parent_contact VARCHAR(255) NOT NULL DEFAULT '';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'students' AND column_name = 'notes') THEN
        ALTER TABLE students ADD COLUMN notes TEXT NOT NULL DEFAULT '';
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'lessons' AND column_name = 'lesson_time') THEN
        ALTER TABLE lessons ADD COLUMN lesson_time VARCHAR(5) NOT NULL DEFAULT '10:00';
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'lessons' AND column_name = 'is_conducted') THEN
        ALTER TABLE lessons ADD COLUMN is_conducted BOOLEAN NOT NULL DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name = 'lessons' AND column_name = 'homework_prefs') THEN
        ALTER TABLE lessons ADD COLUMN homework_prefs TEXT NOT NULL DEFAULT '';
    END IF;
END $$;
