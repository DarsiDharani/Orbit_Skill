import { Skill } from './skill.model';
import { AdditionalSkill } from './skill.model';

export interface Competency {
  skill: string;
  competency: string;
  current_expertise: string;
  target_expertise: string;
  status: 'Met' | 'Gap' | 'Error';
}

export interface TeamMember {
  id: string;
  name: string;
  skills: Competency[];
  additional_skills?: AdditionalSkill[];
}

export interface ManagerData {
  name: string;
  role: string;
  id: string;
  skills: Competency[];
  team: TeamMember[];
  manager_is_trainer: boolean;
}

export interface TeamAssignmentSubmission {
  id: number;
  training_id: number;
  training_name: string;
  employee_empid: string;
  employee_name: string;
  score: number;
  total_questions: number;
  correct_answers: number;
  submitted_at: string;
  has_feedback?: boolean;
  feedback_count?: number;
}

export interface TeamFeedbackSubmission {
  id: number;
  training_id: number;
  training_name: string;
  employee_empid: string;
  employee_name: string;
  responses: Array<{ questionIndex: number; questionText: string; selectedOption: string }>;
  submitted_at: string;
}

export interface ManagerPerformanceFeedback {
  id: number;
  training_id: number;
  training_name: string;
  employee_empid: string;
  employee_name: string;
  manager_empid: string;
  manager_name: string;
  knowledge_retention?: number;
  practical_application?: number;
  engagement_level?: number;
  improvement_areas?: string;
  strengths?: string;
  overall_performance: number;
  additional_comments?: string;
  created_at: string;
  updated_at: string;
}

