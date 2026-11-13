export type PageKey = 'overview' | 'events' | 'patients' | 'appointments' | 'billing' | 'monitoring'

export interface HealthResponse {
  status: string
}

export interface EventItem {
  id: number
  event_id: string
  event_type: string
  source: string
  entity_id: string
  payload: Record<string, unknown>
  status: string
  validation_error: string | null
  processing_time_ms: number | null
  created_at: string
  processed_at: string | null
}

export interface PaginatedEventsResponse {
  items: EventItem[]
  page: number
  page_size: number
  total: number
  total_pages: number
}

export interface MonitoringSummary {
  total_events: number
  processed_events: number
  failed_events: number
  processing_rate: number
  events_last_minute: number
}

export interface CountByField {
  event_type?: string
  status?: string
  count: number
}

export interface PatientRecord {
  id: number
  external_patient_id: string
  first_name: string
  last_name: string
  date_of_birth: string
  created_at: string
  updated_at: string
}

export interface AppointmentRecord {
  id: number
  external_appointment_id: string
  patient_id: number
  appointment_date: string
  appointment_type: string
  provider: string
  status: string
  created_at: string
}

export interface BillingRecord {
  id: number
  external_billing_id: string
  patient_id: number
  amount: number
  insurance_provider: string
  billing_status: string
  service_date: string
  created_at: string
}
