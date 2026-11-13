import type {
  AppointmentRecord,
  BillingRecord,
  EventItem,
  HealthResponse,
  MonitoringSummary,
  PaginatedEventsResponse,
  PatientRecord,
  CountByField,
} from '../types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(init.headers || {}),
    },
    ...init,
  })

  if (!response.ok) {
    const text = await response.text()
    throw new Error(text || `Request failed (${response.status})`)
  }

  return (await response.json()) as T
}

export const api = {
  health: () => request<HealthResponse>('/health'),

  getSummary: () => request<MonitoringSummary>('/api/monitoring/summary'),

  getEventTypes: () => request<CountByField[]>('/api/monitoring/event-types'),

  getStatusCounts: () => request<CountByField[]>('/api/monitoring/status'),

  getRecentFailures: (limit = 10) => request<EventItem[]>(`/api/monitoring/recent-failures?limit=${limit}`),

  getEvents: (page = 1, pageSize = 20, eventType?: string, status?: string) => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })

    if (eventType) params.set('event_type', eventType)
    if (status) params.set('status', status)

    return request<PaginatedEventsResponse>(`/api/events?${params.toString()}`)
  },

  getEventById: (eventId: string) => request<EventItem>(`/api/events/${eventId}`),

  getPatients: (limit = 100) => request<PatientRecord[]>(`/api/patients?limit=${limit}`),

  getAppointments: (limit = 100) => request<AppointmentRecord[]>(`/api/appointments?limit=${limit}`),

  getBilling: (limit = 100) => request<BillingRecord[]>(`/api/billing?limit=${limit}`),
}

export { API_BASE_URL }
