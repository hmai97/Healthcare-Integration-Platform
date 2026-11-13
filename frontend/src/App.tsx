import { useEffect, useMemo, useState, type ReactNode } from 'react'
import {
  Activity,
  AlertTriangle,
  ArrowUpRight,
  BadgeCheck,
  CalendarDays,
  CreditCard,
  FileText,
  HeartPulse,
  LayoutDashboard,
  MonitorCog,
  Users,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { api } from './lib/api'
import type {
  AppointmentRecord,
  BillingRecord,
  CountByField,
  EventItem,
  PageKey,
  PatientRecord,
} from './types'

const NAV_ITEMS: { key: PageKey; label: string; icon: typeof LayoutDashboard }[] = [
  { key: 'overview', label: 'Overview', icon: LayoutDashboard },
  { key: 'events', label: 'Events', icon: FileText },
  { key: 'patients', label: 'Patients', icon: Users },
  { key: 'appointments', label: 'Appointments', icon: CalendarDays },
  { key: 'billing', label: 'Billing', icon: CreditCard },
  { key: 'monitoring', label: 'System Monitoring', icon: MonitorCog },
]

const FALLBACK_COLORS = ['#1E293B', '#4F817C', '#64748B', '#A5B4FC', '#8DAAB3', '#94A3B8']

function formatDate(value: string | null | undefined) {
  if (!value) return '—'
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function shortenEventId(value: string) {
  if (!value) return '—'
  return value.length > 18 ? `${value.slice(0, 12)}...` : value
}

function formatMoney(value: number) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value)
}

function App() {
  const [activePage, setActivePage] = useState<PageKey>('overview')
  const [summary, setSummary] = useState<any>(null)
  const [eventTypes, setEventTypes] = useState<CountByField[]>([])
  const [statusCounts, setStatusCounts] = useState<CountByField[]>([])
  const [recentFailures, setRecentFailures] = useState<EventItem[]>([])
  const [events, setEvents] = useState<EventItem[]>([])
  const [patients, setPatients] = useState<PatientRecord[]>([])
  const [appointments, setAppointments] = useState<AppointmentRecord[]>([])
  const [billing, setBilling] = useState<BillingRecord[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [eventSearch, setEventSearch] = useState('')
  const [eventTypeFilter, setEventTypeFilter] = useState('all')
  const [eventStatusFilter, setEventStatusFilter] = useState('all')
  const [appliedFilters, setAppliedFilters] = useState({ search: '', type: 'all', status: 'all' })
  const [patientSearch, setPatientSearch] = useState('')
  const [appointmentSearch, setAppointmentSearch] = useState('')
  const [billingSearch, setBillingSearch] = useState('')
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)
  const [selectedEvent, setSelectedEvent] = useState<EventItem | null>(null)
  const [isEventDetailsLoading, setIsEventDetailsLoading] = useState(false)
  const [isEventIdCopied, setIsEventIdCopied] = useState(false)

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true)
      setError(null)

      try {
        const [summaryData, eventTypeData, statusData, failuresData, eventsData, patientsData, appointmentsData, billingData] = await Promise.all([
          api.getSummary(),
          api.getEventTypes(),
          api.getStatusCounts(),
          api.getRecentFailures(5),
          api.getEvents(1, 8),
          api.getPatients(8),
          api.getAppointments(8),
          api.getBilling(8),
        ])

        setSummary(summaryData)
        setEventTypes(eventTypeData)
        setStatusCounts(statusData)
        setRecentFailures(failuresData)
        setEvents(eventsData.items)
        setPatients(patientsData)
        setAppointments(appointmentsData)
        setBilling(billingData)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load dashboard data')
      } finally {
        setIsLoading(false)
      }
    }

    void loadData()
  }, [])

  useEffect(() => {
    if (!selectedEventId) {
      setSelectedEvent(null)
      setIsEventIdCopied(false)
      return
    }

    const loadSelectedEvent = async () => {
      setIsEventDetailsLoading(true)
      try {
        const event = await api.getEventById(selectedEventId)
        setSelectedEvent(event)
      } catch {
        setSelectedEvent(null)
      } finally {
        setIsEventDetailsLoading(false)
      }
    }

    void loadSelectedEvent()
  }, [selectedEventId])

  const eventChartData = useMemo(
    () =>
      eventTypes.map((item, index) => ({
        name: item.event_type ?? 'Unknown',
        value: item.count,
        fill: FALLBACK_COLORS[index % FALLBACK_COLORS.length],
      })),
    [eventTypes],
  )

  const statusChartData = useMemo(
    () =>
      statusCounts.map((item) => ({
        name: item.status ?? 'Unknown',
        value: item.count,
        fill: item.status === 'PROCESSED' ? '#4F817C' : item.status === 'FAILED' ? '#D97706' : '#1E293B',
      })),
    [statusCounts],
  )

  const pageTitle = NAV_ITEMS.find((item) => item.key === activePage)?.label ?? 'Overview'

  const filteredEvents = useMemo(() => {
    return events.filter((event) => {
      const searchText = appliedFilters.search.trim().toLowerCase()
      const matchesSearch =
        searchText.length === 0 ||
        event.event_id.toLowerCase().includes(searchText) ||
        event.entity_id.toLowerCase().includes(searchText) ||
        event.event_type.toLowerCase().includes(searchText)

      const matchesType = appliedFilters.type === 'all' || event.event_type === appliedFilters.type
      const matchesStatus = appliedFilters.status === 'all' || event.status === appliedFilters.status

      return matchesSearch && matchesType && matchesStatus
    })
  }, [appliedFilters, events])

  const filteredPatients = useMemo(() => {
    const query = patientSearch.trim().toLowerCase()
    return patients.filter((patient) => {
      if (!query) return true
      return [patient.external_patient_id, patient.first_name, patient.last_name, patient.date_of_birth]
        .join(' ')
        .toLowerCase()
        .includes(query)
    })
  }, [patientSearch, patients])

  const filteredAppointments = useMemo(() => {
    const query = appointmentSearch.trim().toLowerCase()
    return appointments.filter((appointment) => {
      if (!query) return true
      return [appointment.external_appointment_id, appointment.provider, appointment.appointment_type, appointment.status]
        .join(' ')
        .toLowerCase()
        .includes(query)
    })
  }, [appointmentSearch, appointments])

  const filteredBilling = useMemo(() => {
    const query = billingSearch.trim().toLowerCase()
    return billing.filter((item) => {
      if (!query) return true
      return [item.external_billing_id, item.insurance_provider, item.billing_status, item.patient_id.toString()]
        .join(' ')
        .toLowerCase()
        .includes(query)
    })
  }, [billing, billingSearch])

  useEffect(() => {
    if (selectedEventId && !filteredEvents.some((event) => event.event_id === selectedEventId)) {
      setSelectedEventId(null)
    }
  }, [filteredEvents, selectedEventId])

  const copyEventId = async (eventId: string) => {
    try {
      await navigator.clipboard.writeText(eventId)
      setIsEventIdCopied(true)
      window.setTimeout(() => setIsEventIdCopied(false), 1500)
    } catch {
      setIsEventIdCopied(false)
    }
  }

  if (isLoading) {
    return <DashboardShell activePage={activePage} setActivePage={setActivePage}><LoadingState /></DashboardShell>
  }

  if (error) {
    return <DashboardShell activePage={activePage} setActivePage={setActivePage}><ErrorState message={error} /></DashboardShell>
  }

  const renderOverview = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <MetricCard title="Total Events" value={summary?.total_events ?? 0} icon={<FileText className="h-5 w-5" />} accent="navy" />
        <MetricCard title="Processed Events" value={summary?.processed_events ?? 0} icon={<BadgeCheck className="h-5 w-5" />} accent="green" />
        <MetricCard title="Failed Events" value={summary?.failed_events ?? 0} icon={<AlertTriangle className="h-5 w-5" />} accent="amber" />
        <MetricCard title="Success Rate" value={`${summary?.processing_rate ?? 0}%`} icon={<Activity className="h-5 w-5" />} accent="teal" />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Events by Type">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={eventChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#1E293B" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Processing Status">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={statusChartData} dataKey="value" nameKey="name" innerRadius={56} outerRadius={82} paddingAngle={3}>
                  {statusChartData.map((entry) => <Cell key={entry.name} fill={entry.fill} />)}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <Panel title="Recent Events">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[900px] table-fixed text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="w-[18%] py-3 pr-6 font-medium text-left">Event ID</th>
                <th className="w-[15%] py-3 pr-6 font-medium text-left">Type</th>
                <th className="hidden md:table-cell w-[15%] py-3 pr-6 font-medium text-left">Source</th>
                <th className="w-[16%] py-3 pr-6 font-medium text-left">Entity ID</th>
                <th className="w-[18%] py-3 pr-6 font-medium text-left">Timestamp</th>
                <th className="w-[12%] py-3 pr-6 font-medium text-left">Status</th>
              </tr>
            </thead>
            <tbody>
              {events.map((event) => (
                <tr key={event.event_id} className="border-b border-slate-100 last:border-0 transition hover:bg-slate-50">
                  <td className="py-3 pr-6 text-slate-700">{shortenEventId(event.event_id)}</td>
                  <td className="break-words py-3 pr-6 text-slate-700">{event.event_type}</td>
                  <td className="hidden md:table-cell break-words py-3 pr-6 text-slate-700">{event.source}</td>
                  <td className="break-words py-3 pr-6 text-slate-700">{event.entity_id}</td>
                  <td className="whitespace-nowrap py-3 pr-6 text-slate-700">{formatDate(event.created_at)}</td>
                  <td className="py-3 pr-6"><StatusBadge status={event.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )

  const renderEvents = () => (
    <Panel title="Event Activity" className="overflow-hidden">
      <div className="space-y-4">
        <div className="grid gap-3 md:grid-cols-4">
          <input
            value={eventSearch}
            onChange={(e) => setEventSearch(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none ring-0 transition focus:border-[#4F817C]"
            placeholder="Search event id or entity"
          />
          <select
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-[#4F817C]"
          >
            <option value="all">All types</option>
            <option value="PATIENT_CREATED">PATIENT_CREATED</option>
            <option value="APPOINTMENT_CREATED">APPOINTMENT_CREATED</option>
            <option value="BILLING_CREATED">BILLING_CREATED</option>
          </select>
          <select
            value={eventStatusFilter}
            onChange={(e) => setEventStatusFilter(e.target.value)}
            className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none focus:border-[#4F817C]"
          >
            <option value="all">All status</option>
            <option value="PROCESSED">PROCESSED</option>
            <option value="FAILED">FAILED</option>
            <option value="VALIDATED">VALIDATED</option>
          </select>
          <button
            type="button"
            onClick={() => setAppliedFilters({
              search: eventSearch,
              type: eventTypeFilter,
              status: eventStatusFilter,
            })}
            className="rounded-xl bg-[#4F817C] px-3 py-2 text-sm font-medium text-white transition hover:bg-[#436f6a]"
          >
            Apply Filters
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[1100px] table-fixed text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="w-[18%] py-3 pr-6 font-medium text-left">Event ID</th>
                <th className="w-[15%] py-3 pr-6 font-medium text-left">Type</th>
                <th className="hidden md:table-cell w-[15%] py-3 pr-6 font-medium text-left">Source</th>
                <th className="w-[16%] py-3 pr-6 font-medium text-left">Entity ID</th>
                <th className="w-[18%] py-3 pr-6 font-medium text-left">Timestamp</th>
                <th className="w-[12%] py-3 pr-6 font-medium text-left">Status</th>
                <th className="w-[16%] py-3 font-medium text-left">Validation</th>
              </tr>
            </thead>
            <tbody>
              {filteredEvents.map((event) => (
                <tr
                  key={event.event_id}
                  className="cursor-pointer border-b border-slate-100 last:border-0 transition hover:bg-slate-50"
                  onClick={() => setSelectedEventId(event.event_id)}
                >
                  <td className="py-3 pr-6 text-slate-700">{shortenEventId(event.event_id)}</td>
                  <td className="py-3 pr-6 text-slate-700">{event.event_type}</td>
                  <td className="hidden md:table-cell py-3 pr-6 text-slate-700">{event.source}</td>
                  <td className="py-3 pr-6 text-slate-700">{event.entity_id}</td>
                  <td className="whitespace-nowrap py-3 pr-6 text-slate-700">{formatDate(event.created_at)}</td>
                  <td className="py-3 pr-6"><StatusBadge status={event.status} /></td>
                  <td className="py-3 text-slate-700">{event.validation_error ?? ''}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedEventId && (
          <div className="mt-5 rounded-2xl border border-slate-200 bg-slate-50 p-4">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Event Details</p>
                <h3 className="mt-1 text-lg font-semibold text-slate-900">{selectedEvent?.event_id ?? selectedEventId}</h3>
              </div>
              <button
                type="button"
                onClick={() => copyEventId(selectedEvent?.event_id ?? selectedEventId)}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm font-medium text-slate-700 transition hover:border-[#4F817C] hover:text-[#4F817C]"
              >
                {isEventIdCopied ? 'Copied' : 'Copy Event ID'}
              </button>
            </div>

            {isEventDetailsLoading ? (
              <p className="text-sm text-slate-500">Loading event details...</p>
            ) : selectedEvent ? (
              <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
                <div className="rounded-xl bg-white p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Event ID</p>
                  <p className="mt-2 break-all text-sm font-medium text-slate-900">{selectedEvent.event_id}</p>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Type</p>
                  <p className="mt-2 text-sm font-medium text-slate-900">{selectedEvent.event_type}</p>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Source</p>
                  <p className="mt-2 text-sm font-medium text-slate-900">{selectedEvent.source}</p>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Entity ID</p>
                  <p className="mt-2 break-all text-sm font-medium text-slate-900">{selectedEvent.entity_id}</p>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Status</p>
                  <p className="mt-2 text-sm font-medium text-slate-900"><StatusBadge status={selectedEvent.status} /></p>
                </div>
                <div className="rounded-xl bg-white p-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Created</p>
                  <p className="mt-2 text-sm font-medium text-slate-900">{formatDate(selectedEvent.created_at)}</p>
                </div>
                <div className="rounded-xl bg-white p-3 md:col-span-2 xl:col-span-3">
                  <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Payload</p>
                  <pre className="mt-2 overflow-x-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-100">{JSON.stringify(selectedEvent.payload, null, 2)}</pre>
                </div>
              </div>
            ) : (
              <p className="text-sm text-red-600">Unable to load event details for this record.</p>
            )}
          </div>
        )}
      </div>
    </Panel>
  )

  const renderPatients = () => (
    <Panel title="Patients">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <input
            value={patientSearch}
            onChange={(e) => setPatientSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[#4F817C]"
            placeholder="Search patient, ID, or DOB"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-3 font-medium">ID</th>
                <th className="py-3 font-medium">External Patient ID</th>
                <th className="py-3 font-medium">First Name</th>
                <th className="py-3 font-medium">Last Name</th>
                <th className="py-3 font-medium">Date of Birth</th>
                <th className="py-3 font-medium">Created</th>
              </tr>
            </thead>
            <tbody>
              {filteredPatients.map((patient) => (
                <tr key={patient.id} className="border-b border-slate-100 last:border-0 transition hover:bg-slate-50">
                  <td className="py-3 text-slate-700">{patient.id}</td>
                  <td className="py-3 text-slate-700">{patient.external_patient_id}</td>
                  <td className="py-3 text-slate-700">{patient.first_name}</td>
                  <td className="py-3 text-slate-700">{patient.last_name}</td>
                  <td className="py-3 text-slate-700">{patient.date_of_birth}</td>
                  <td className="py-3 text-slate-700">{formatDate(patient.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  )

  const renderAppointments = () => (
    <Panel title="Appointments">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <input
            value={appointmentSearch}
            onChange={(e) => setAppointmentSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[#4F817C]"
            placeholder="Search provider, type, or status"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-3 font-medium">ID</th>
                <th className="py-3 font-medium">External ID</th>
                <th className="py-3 font-medium">Patient ID</th>
                <th className="py-3 font-medium">Appointment Date</th>
                <th className="py-3 font-medium">Type</th>
                <th className="py-3 font-medium">Provider</th>
                <th className="py-3 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredAppointments.map((appointment) => (
                <tr key={appointment.id} className="border-b border-slate-100 last:border-0 transition hover:bg-slate-50">
                  <td className="py-3 text-slate-700">{appointment.id}</td>
                  <td className="py-3 text-slate-700">{appointment.external_appointment_id}</td>
                  <td className="py-3 text-slate-700">{appointment.patient_id}</td>
                  <td className="py-3 text-slate-700">{appointment.appointment_date}</td>
                  <td className="py-3 text-slate-700">{appointment.appointment_type}</td>
                  <td className="py-3 text-slate-700">{appointment.provider}</td>
                  <td className="py-3"><StatusBadge status={appointment.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  )

  const renderBilling = () => (
    <Panel title="Billing Records">
      <div className="space-y-4">
        <div className="flex items-center gap-3">
          <input
            value={billingSearch}
            onChange={(e) => setBillingSearch(e.target.value)}
            className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-700 outline-none transition focus:border-[#4F817C]"
            placeholder="Search billing ID, insurer, or status"
          />
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[800px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-3 font-medium">ID</th>
                <th className="py-3 font-medium">External ID</th>
                <th className="py-3 font-medium">Patient ID</th>
                <th className="py-3 font-medium">Amount</th>
                <th className="py-3 font-medium">Insurance</th>
                <th className="py-3 font-medium">Status</th>
                <th className="py-3 font-medium">Service Date</th>
              </tr>
            </thead>
            <tbody>
              {filteredBilling.map((item) => (
                <tr key={item.id} className="border-b border-slate-100 last:border-0 transition hover:bg-slate-50">
                  <td className="py-3 text-slate-700">{item.id}</td>
                  <td className="py-3 text-slate-700">{item.external_billing_id}</td>
                  <td className="py-3 text-slate-700">{item.patient_id}</td>
                  <td className="py-3 text-slate-700">{formatMoney(item.amount)}</td>
                  <td className="py-3 text-slate-700">{item.insurance_provider}</td>
                  <td className="py-3"><StatusBadge status={item.billing_status} /></td>
                  <td className="py-3 text-slate-700">{item.service_date}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </Panel>
  )

  const renderMonitoring = () => (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-3">
        <MetricCard title="API Health" value="Available" icon={<HeartPulse className="h-5 w-5" />} accent="teal" />
        <MetricCard title="Processed" value={summary?.processed_events ?? 0} icon={<BadgeCheck className="h-5 w-5" />} accent="green" />
        <MetricCard title="Failures" value={summary?.failed_events ?? 0} icon={<AlertTriangle className="h-5 w-5" />} accent="amber" />
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <Panel title="Event Counts by Type">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={eventChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#4F817C" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>

        <Panel title="Event Counts by Status">
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={statusChartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#E5E7EB" />
                <XAxis dataKey="name" tick={{ fontSize: 12 }} />
                <YAxis tick={{ fontSize: 12 }} />
                <Tooltip />
                <Bar dataKey="value" radius={[8, 8, 0, 0]} fill="#1E293B" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Panel>
      </div>

      <Panel title="Recent Failures">
        <div className="overflow-x-auto">
          <table className="w-full min-w-[700px] text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-slate-500">
                <th className="py-3 font-medium">Event ID</th>
                <th className="py-3 font-medium">Type</th>
                <th className="py-3 font-medium">Entity ID</th>
                <th className="py-3 font-medium">Timestamp</th>
                <th className="py-3 font-medium">Error</th>
              </tr>
            </thead>
            <tbody>
              {recentFailures.map((event) => (
                <tr key={event.event_id} className="border-b border-slate-100 last:border-0 align-top">
                  <td className="py-3 text-slate-700">{event.event_id}</td>
                  <td className="py-3 text-slate-700">{event.event_type}</td>
                  <td className="py-3 text-slate-700">{event.entity_id}</td>
                  <td className="py-3 text-slate-700">{formatDate(event.created_at)}</td>
                  <td className="py-3 text-slate-700">{event.validation_error ?? '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  )

  let content
  switch (activePage) {
    case 'events':
      content = renderEvents()
      break
    case 'patients':
      content = renderPatients()
      break
    case 'appointments':
      content = renderAppointments()
      break
    case 'billing':
      content = renderBilling()
      break
    case 'monitoring':
      content = renderMonitoring()
      break
    default:
      content = renderOverview()
  }

  return (
    <DashboardShell activePage={activePage} setActivePage={setActivePage}>
      <header className="mb-6 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.25em] text-slate-500">Healthcare Integration</p>
          <h1 className="mt-2 text-3xl font-semibold text-slate-900">{pageTitle}</h1>
        </div>
        <div className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
          <span className="inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
          API status: healthy
        </div>
      </header>
      {content}
    </DashboardShell>
  )
}

function DashboardShell({
  children,
  activePage,
  setActivePage,
}: {
  children: ReactNode
  activePage: PageKey
  setActivePage: React.Dispatch<React.SetStateAction<PageKey>>
}) {
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)

  return (
    <div className="min-h-screen bg-[#F8F9FA] text-slate-900">
      <div className="flex min-h-screen flex-col lg:flex-row">
        <aside className={`${isSidebarCollapsed ? 'lg:w-20' : 'lg:w-72'} w-full bg-[#1E293B] px-5 py-6 text-slate-100 transition-all duration-200 lg:min-h-screen lg:border-r lg:border-slate-700`}>
          <div className="mb-8 flex items-center justify-between gap-3 px-2">
            <div className="flex items-center gap-3 overflow-hidden">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#4F817C] text-white">
                <HeartPulse className="h-5 w-5" />
              </div>
              {!isSidebarCollapsed && (
                <div className="overflow-hidden">
                  <div className="text-sm font-semibold tracking-[0.18em] text-slate-300">HEALTHCARE</div>
                  <div className="text-lg font-semibold text-white">Data Platform</div>
                </div>
              )}
            </div>
            <button
              type="button"
              onClick={() => setIsSidebarCollapsed((value) => !value)}
              className="hidden rounded-lg border border-slate-600 px-2 py-1 text-xs text-slate-200 transition hover:bg-slate-700 lg:inline-flex"
            >
              {isSidebarCollapsed ? '>' : '<'}
            </button>
          </div>

          <nav className="space-y-2">
            {NAV_ITEMS.map(({ key, label, icon: Icon }) => (
              <button
                key={key}
                type="button"
                onClick={() => setActivePage(key)}
                className={`flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left text-sm font-medium transition hover:-translate-y-0.5 hover:bg-slate-700/60 ${activePage === key ? 'bg-[#4F817C] text-white shadow-sm' : 'text-slate-200'}`}
                title={label}
              >
                <Icon className="h-4 w-4 shrink-0" />
                {!isSidebarCollapsed && <span>{label}</span>}
              </button>
            ))}
          </nav>
        </aside>

        <main className="flex-1 p-4 md:p-6 xl:p-8">{children}</main>
      </div>
    </div>
  )
}

function MetricCard({ title, value, icon, accent }: { title: string; value: string | number; icon: ReactNode; accent: 'navy' | 'green' | 'amber' | 'teal' }) {
  const accentColors = {
    navy: 'bg-[#1E293B] text-white',
    green: 'bg-emerald-50 text-emerald-700',
    amber: 'bg-amber-50 text-amber-700',
    teal: 'bg-[#E6F1F1] text-[#4F817C]',
  }

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-sm text-slate-500">{title}</p>
          <p className="mt-3 text-3xl font-semibold text-slate-900">{value}</p>
        </div>
        <div className={`flex h-11 w-11 items-center justify-center rounded-xl ${accentColors[accent]}`}>
          {icon}
        </div>
      </div>
    </div>
  )
}

function Panel({ title, children, className = '' }: { title: string; children: ReactNode; className?: string }) {
  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm md:p-5">
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        <ArrowUpRight className="h-4 w-4 text-slate-400" />
      </div>
      <div className={className}>{children}</div>
    </section>
  )
}

function StatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    PROCESSED: 'bg-emerald-100 text-emerald-700',
    FAILED: 'bg-amber-100 text-amber-700',
    VALIDATED: 'bg-sky-100 text-sky-700',
    RECEIVED: 'bg-slate-100 text-slate-700',
    SCHEDULED: 'bg-sky-100 text-sky-700',
    PENDING: 'bg-amber-100 text-amber-700',
    PAID: 'bg-emerald-100 text-emerald-700',
    DENIED: 'bg-red-100 text-red-700',
    CANCELLED: 'bg-slate-200 text-slate-700',
    COMPLETED: 'bg-emerald-100 text-emerald-700',
  }

  return (
    <span className={`inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${map[status] ?? 'bg-slate-100 text-slate-700'}`}>
      {status}
    </span>
  )
}

function LoadingState() {
  return (
    <div className="flex min-h-[420px] items-center justify-center rounded-2xl border border-slate-200 bg-white text-slate-600 shadow-sm">
      Loading dashboard data...
    </div>
  )
}

function ErrorState({ message }: { message: string }) {
  return (
    <div className="flex min-h-[420px] items-center justify-center rounded-2xl border border-red-200 bg-red-50 p-6 text-center text-red-700 shadow-sm">
      <div>
        <p className="text-lg font-semibold">Unable to load dashboard</p>
        <p className="mt-2 text-sm">{message}</p>
      </div>
    </div>
  )
}

export default App
