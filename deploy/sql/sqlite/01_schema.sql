-- RepetCRM: полная схема БД (SQLite 3)
-- Запуск: sqlite3 data/repetcrm.db < deploy/sql/sqlite/01_schema.sql

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    email                VARCHAR(255) NOT NULL UNIQUE,
    hashed_password      VARCHAR(255) NOT NULL,
    name                 VARCHAR(255) NOT NULL DEFAULT '',
    onboarding_completed BOOLEAN NOT NULL DEFAULT 0,
    subjects             TEXT NOT NULL DEFAULT '[]',
    grade_levels         TEXT NOT NULL DEFAULT '[]',
    teaching_format      VARCHAR(50) NOT NULL DEFAULT '',
    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS students (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id        INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name            VARCHAR(255) NOT NULL,
    subject         VARCHAR(255) NOT NULL DEFAULT '',
    grade           VARCHAR(50) NOT NULL DEFAULT '',
    school          VARCHAR(255) NOT NULL DEFAULT '',
    contact         VARCHAR(255) NOT NULL DEFAULT '',
    parent_contact  VARCHAR(255) NOT NULL DEFAULT '',
    notes           TEXT NOT NULL DEFAULT '',
    created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS lessons (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    tutor_id         INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_id       INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    lesson_date      DATE NOT NULL,
    lesson_time      VARCHAR(5) NOT NULL DEFAULT '10:00',
    duration_minutes INTEGER NOT NULL DEFAULT 60,
    payment_amount   REAL NOT NULL DEFAULT 0,
    is_paid          BOOLEAN NOT NULL DEFAULT 0,
    is_conducted     BOOLEAN NOT NULL DEFAULT 0,
    homework_prefs   TEXT NOT NULL DEFAULT '',
    notes            TEXT NOT NULL DEFAULT '',
    created_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS checklist_items (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id     INTEGER NOT NULL REFERENCES lessons(id) ON DELETE CASCADE,
    topic         VARCHAR(500) NOT NULL,
    work_type     VARCHAR(50) NOT NULL DEFAULT 'practice',
    difficulty    VARCHAR(50) NOT NULL DEFAULT 'medium',
    understanding INTEGER NOT NULL DEFAULT 3
);

CREATE TABLE IF NOT EXISTS homeworks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    lesson_id     INTEGER NOT NULL UNIQUE REFERENCES lessons(id) ON DELETE CASCADE,
    homework_text TEXT NOT NULL DEFAULT '',
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_students_tutor_id ON students(tutor_id);
CREATE INDEX IF NOT EXISTS idx_lessons_tutor_id ON lessons(tutor_id);
CREATE INDEX IF NOT EXISTS idx_lessons_student_id ON lessons(student_id);
CREATE INDEX IF NOT EXISTS idx_lessons_date ON lessons(lesson_date);
CREATE INDEX IF NOT EXISTS idx_checklist_lesson_id ON checklist_items(lesson_id);
