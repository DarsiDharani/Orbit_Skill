export interface TrainingDetail {
  id: number;
  division?: string;
  department?: string;
  competency?: string;
  skill?: string;
  training_name: string;
  training_topics?: string;
  prerequisites?: string;
  skill_category?: string;
  trainer_name: string;
  email?: string;
  training_date?: string;
  duration?: string;
  time?: string;
  training_type?: string;
  seats?: string;
  assessment_details?: string;
  assignmentType?: 'personal' | 'team'; // Added to distinguish between personal and team assignments
  assigned_to?: string; // Added for team assigned trainings
}

export interface TrainingRequest {
  id: number;
  training_id: number;
  employee_empid: string;
  manager_empid: string;
  request_date: string;
  status: 'pending' | 'approved' | 'rejected';
  manager_notes?: string;
  response_date?: string;
  training: TrainingDetail;
  employee?: {
    username: string;
    name?: string;
  };
}

export interface CalendarEvent {
  date: Date;
  title: string;
  trainer: string;
}

