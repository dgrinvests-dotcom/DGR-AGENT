// Type definitions for the AI Real Estate Agent Dashboard

export interface Lead {
  id: string;
  first_name: string;
  last_name: string;
  phone: string;
  email?: string;
  property_address: string;
  property_type: PropertyType;
  status: LeadStatus;
  campaign_id?: string;
  created_at: string;
  last_contact_date?: string;
  next_follow_up_date?: string;
  property_value?: number;
  condition?: string;
  notes?: string;
}

export interface Campaign {
  id: string;
  name: string;
  property_type: PropertyType;
  status: CampaignStatus;
  created_at: string;
  updated_at: string;
  config: CampaignConfig;
  stats: CampaignStats;
}

export interface CampaignConfig {
  max_daily_contacts: number;
  follow_up_days: number[];
  target_response_rate: number;
  quiet_hours_start: string;
  quiet_hours_end: string;
}

export interface CampaignStats {
  total_leads: number;
  contacted_leads: number;
  responded_leads: number;
  appointments_set: number;
  response_rate: number;
  conversion_rate: number;
}

export interface Conversation {
  id: string;
  lead_id: string;
  messages: ConversationMessage[];
  status: ConversationStatus;
  created_at: string;
  updated_at: string;
}

export interface ConversationMessage {
  id: string;
  direction: 'inbound' | 'outbound';
  content: string;
  timestamp: string;
  method: 'sms' | 'email';
  ai_generated: boolean;
}

export interface DashboardStats {
  active_campaigns: number;
  total_leads: number;
  active_conversations: number;
  appointments_today: number;
  response_rate: number;
  conversion_rate: number;
}

export enum PropertyType {
  FIX_FLIP = 'fix_flip',
  RENTAL = 'rental',
  VACANT_LAND = 'vacant_land'
}

export enum LeadStatus {
  NEW = 'new',
  CONTACTED = 'contacted',
  RESPONDED = 'responded',
  QUALIFIED = 'qualified',
  APPOINTMENT_SET = 'appointment_set',
  NO_SHOW = 'no_show',
  NOT_INTERESTED = 'not_interested',
  OPTED_OUT = 'opted_out'
}

export enum CampaignStatus {
  CREATED = 'created',
  ACTIVE = 'active',
  PAUSED = 'paused',
  STOPPED = 'stopped',
  COMPLETED = 'completed'
}

export enum ConversationStatus {
  ACTIVE = 'active',
  WAITING_RESPONSE = 'waiting_response',
  QUALIFIED = 'qualified',
  APPOINTMENT_SET = 'appointment_set',
  CLOSED = 'closed'
}

export interface ApiResponse<T> {
  data: T;
  message?: string;
  success: boolean;
}

export interface LeadImportResult {
  imported: number;
  skipped: number;
  errors: string[];
}

export interface IntegrationStatus {
  telnyx: boolean;
  google_meet: boolean;
  gmail: boolean;
  openai: boolean;
}
