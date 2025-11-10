export interface QuestionOption {
  text: string;
  isCorrect: boolean;
}

export interface AssignmentQuestion {
  text: string;
  helperText: string; // Optional helper text like "Please select at most 2 options."
  type: 'single-choice' | 'multiple-choice' | 'text-input';
  options: QuestionOption[];
}

export interface Assignment {
  trainingId: number | null;
  title: string;
  description: string;
  questions: AssignmentQuestion[];
  sharedAssignmentId?: number;
}

export interface UserAnswer {
  questionIndex: number;
  type: string;
  selectedOptions: number[];
  textAnswer?: string;
}

export interface QuestionResult {
  questionIndex: number;
  isCorrect: boolean;
  correctAnswers: number[];
  userAnswers: number[];
  userTextAnswer?: string;
}

export interface AssignmentResult {
  id: number;
  training_id: number;
  score: number;
  total_questions: number;
  correct_answers: number;
  question_results: QuestionResult[];
  submitted_at: string;
}

export interface FeedbackQuestion {
  text: string;
  options: string[];
  isDefault: boolean;
}

