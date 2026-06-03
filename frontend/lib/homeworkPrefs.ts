export type HomeworkPrefs = {
  focus_aspect: string;
  student_level: string;
  understanding_global: number;
  task_types: string[];
  volume: string;
  difficulty_level: string;
  special_notes: string;
  output_formats: string[];
  include_cheatsheet: boolean;
  include_hints: boolean;
  include_examples: boolean;
};

export const defaultHomeworkPrefs = (): HomeworkPrefs => ({
  focus_aspect: "mixed",
  student_level: "medium",
  understanding_global: 3,
  task_types: ["practice_rules", "text_problems"],
  volume: "standard",
  difficulty_level: "medium",
  special_notes: "",
  output_formats: ["latex"],
  include_cheatsheet: false,
  include_hints: false,
  include_examples: false,
});
