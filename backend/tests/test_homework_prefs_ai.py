"""AI homework prompt sizing."""

from app.services.homework_prefs import DEFAULT_HOMEWORK_PREFS, tasks_per_topic_for_ai


def test_tasks_per_topic_scales_with_topic_count():
    assert tasks_per_topic_for_ai(DEFAULT_HOMEWORK_PREFS, 1) == ("6", "9")
    assert tasks_per_topic_for_ai(DEFAULT_HOMEWORK_PREFS, 2) == ("4", "6")
    assert tasks_per_topic_for_ai(DEFAULT_HOMEWORK_PREFS, 3) == ("3", "4")
