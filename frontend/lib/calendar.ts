const WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

const MONTHS = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
];

export function toDateKey(d: Date): string {
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function parseDateKey(key: string): Date {
  const [y, m, d] = key.split("-").map(Number);
  return new Date(y, m - 1, d);
}

export function formatMonthYear(year: number, month: number): string {
  return `${MONTHS[month]} ${year}`;
}

export function formatDayLabel(key: string): string {
  return parseDateKey(key).toLocaleDateString("ru-RU", {
    weekday: "long",
    day: "numeric",
    month: "long",
  });
}

export function formatLessonTime(time: string | undefined): string {
  if (!time) return "";
  return time.slice(0, 5);
}

export function compareLessonTime(a: string, b: string): number {
  return formatLessonTime(a).localeCompare(formatLessonTime(b));
}

export { WEEKDAYS };

export type CalendarCell = {
  date: Date;
  dateKey: string;
  inMonth: boolean;
  isToday: boolean;
};

/** Сетка 6×7, неделя с понедельника */
export function buildMonthGrid(year: number, month: number): CalendarCell[] {
  const todayKey = toDateKey(new Date());
  const first = new Date(year, month, 1);
  const startOffset = (first.getDay() + 6) % 7;
  const start = new Date(year, month, 1 - startOffset);

  const cells: CalendarCell[] = [];
  for (let i = 0; i < 42; i++) {
    const date = new Date(start);
    date.setDate(start.getDate() + i);
    const dateKey = toDateKey(date);
    cells.push({
      date,
      dateKey,
      inMonth: date.getMonth() === month,
      isToday: dateKey === todayKey,
    });
  }
  return cells;
}
