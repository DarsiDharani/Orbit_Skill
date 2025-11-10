export interface Skill {
  id: number;
  skill: string;
  competency: string;
  current_expertise: string;
  target_expertise: string;
  status: 'Met' | 'Gap' | 'Error';
}

export interface ModalSkill {
  id: number;
  skill: string;
  competency: string;
  current_expertise?: string;
  target_expertise?: string;
  status?: 'Met' | 'Gap' | 'Error';
}

export interface AdditionalSkill {
  id: number;
  skill_name: string;
  skill_level: string;
  skill_category: string;
  description?: string;
  created_at?: string;
}

