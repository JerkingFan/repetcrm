-- SQLite: datetime columns with non-constant defaults (fix for ALTER TABLE limits)
-- Run manually if backend failed on boundary_updated_at / status_changed_at:

-- students.boundary_updated_at
ALTER TABLE students ADD COLUMN boundary_updated_at DATETIME;
UPDATE students SET boundary_updated_at = COALESCE(created_at, datetime('now'))
  WHERE boundary_updated_at IS NULL;

-- lessons.status / late_minutes / rescheduled (if missing)
-- ALTER TABLE lessons ADD COLUMN status VARCHAR(20) DEFAULT 'scheduled';
-- ALTER TABLE lessons ADD COLUMN late_minutes INTEGER DEFAULT 0;
-- ALTER TABLE lessons ADD COLUMN rescheduled_from_lesson_id INTEGER;

-- lessons.status_changed_at
ALTER TABLE lessons ADD COLUMN status_changed_at DATETIME;
UPDATE lessons SET status_changed_at = COALESCE(created_at, datetime('now'))
  WHERE status_changed_at IS NULL;
