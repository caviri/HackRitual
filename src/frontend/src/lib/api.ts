/**
 * Thin wrapper around the FastAPI backend served by the same container.
 *
 * Two patterns:
 *
 *   • `fetchJson<T>(path, fallback)` — returns `fallback` if the request
 *     fails (network down, 4xx/5xx, JSON parse error). Used during the
 *     proposal phase when the backend may not be deployed alongside the
 *     static export.
 *
 *   • `requireJson<T>(path)` — throws on any failure. Use for forms.
 *
 * Endpoints map 1:1 to the FastAPI routers under /api/*.
 */

export type EventState = 'DRAFT' | 'OPEN' | 'FROZEN' | 'FINAL' | 'ARCHIVED';
export type ImageEffect = 'none' | 'dither' | 'halftone';
export type ProjectStatus = 'proposed' | 'approved' | 'rejected';
export type SubmissionStatus = 'draft' | 'final' | 'withdrawn';

export interface EventDTO {
  id: string;
  title: string;
  type: string;
  state: EventState;
  // The live API returns start/end; start_at/end_at kept for older callers.
  start?: string;
  end?: string;
  start_at?: string;
  end_at?: string;
  created_at: string;
  updated_at: string;
}

export interface TrackDTO {
  id: string;
  event_id: string;
  name: string;
  description: string | null;
  created_at: string;
  modified_at: string;
}

export interface PhaseDTO {
  id: string;
  event_id: string;
  name: string;
  description: string | null;
  starts_at: string | null;
  ends_at: string | null;
  created_at: string;
  modified_at: string;
}

export interface PageDTO {
  id: string;
  event_id: string;
  title: string;
  content: string;
  visible: boolean;
  order: number;
  phase_id: string | null;
  created_at: string;
  modified_at: string;
}

export interface ProjectDTO {
  id: string;
  event_id: string;
  track_id: string | null;
  proposed_by_participant_id: string;
  title: string;
  description: string;
  image: string | null;
  status: ProjectStatus;
  created_at: string;
  modified_at: string;
}

export interface SubmissionDTO {
  id: string;
  event_id: string;
  project_id: string;
  participant_id: string;
  version: number;
  title: string | null;
  description: string | null;
  result: string | null;
  payload_json: string | null;
  status: SubmissionStatus;
  created_at: string;
  modified_at: string;
}

export interface ParticipantDTO {
  image?: string | null;
  is_waiting?: boolean;
  id: string;
  event_id: string;
  type: 'human' | 'agent' | 'team';
  display_name: string;
  affiliation: string | null;
  links?: string[] | null;
  status: string;
  created_at?: string;
}

export interface ScoreDTO {
  id: string;
  submission_id: string;
  score_value: number;
  breakdown: Record<string, number>;
  notes: string | null;
  status: string;
  scorer_version: string | null;
  scored_at: string | null;
}

export interface LogEntryDTO {
  id: string;
  ts: string;
  actor: string | null;
  actor_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  summary: string | null;
}

export interface LogPageDTO {
  entries: LogEntryDTO[];
  total: number;
  limit: number;
  offset: number;
}

export interface CommitDTO {
  sha: string;
  sha_short: string;
  branch: string | null;
  message: string;
  message_first_line: string;
  author_name: string;
  author_login: string | null;
  author_avatar_url: string | null;
  author_profile_url: string | null;
  committed_at: string;
}

export interface RepoDTO {
  id: string;
  project_id: string;
  url: string;
  host: string;
  owner: string;
  repo: string;
  label: string | null;
  default_branch: string | null;
  description: string | null;
  stars: number | null;
  last_pushed_at: string | null;
  last_polled_at: string | null;
  polling_error: string | null;
  commits: CommitDTO[];
}

export interface AgentDTO {
  id: string;
  name: string;
  owner_user_id: string | null;
  owner_email: string | null;
  status: string;
  created_at: string;
  key_preview: string;
}

export interface AgentCreatedDTO {
  agent: AgentDTO;
  api_key: string;
}

export interface PortraitInfo {
  url: string | null;
  effect: ImageEffect | null;
  contrast: number | null;
  brightness: number | null;
  scale: number | null;
}

export interface MeParticipantDTO {
  id: string;
  display_name: string;
  type: 'human' | 'agent' | 'team';
  status: string;
  is_waiting: boolean;
  affiliation: string | null;
}

export interface MeDTO {
  id: string;
  email: string;
  role: string;
  display_name: string | null;
  participant?: MeParticipantDTO | null;
  portrait?: PortraitInfo | null;
}

export interface LeaderboardParticipantDTO {
  id: string;
  display_name: string;
  type: 'human' | 'agent' | 'team';
}

export interface LeaderboardProjectDTO {
  id: string;
  title: string;
  track_id: string | null;
}

export interface LeaderboardEntryDTO {
  project?: LeaderboardProjectDTO | null;
  rank: number;
  participant: LeaderboardParticipantDTO;
  score: number;
  submission_count: number;
  last_submission_at: string | null;
}

export interface LeaderboardDTO {
  event_id: string;
  event_state: EventState;
  leaderboard_mode: string;
  entries: LeaderboardEntryDTO[];
}

export interface StateTransitionDTO {
  id: string;
  state: EventState;
  previous_state: EventState;
  transitioned_at: string;
  transitioned_by: string;
}

export interface AdminAuditEntryDTO {
  id: string;
  action: string;
  actor_user_id: string | null;
  target_type: string | null;
  target_id: string | null;
  metadata: Record<string, unknown> | null;
  created_at: string | null;
}

export interface AdminDashboardDTO {
  event: {
    id: string;
    title: string;
    state: EventState | 'UNKNOWN';
    start: string | null;
    end: string | null;
  };
  metrics: {
    participants_total: number;
    participants_by_type: Record<string, number>;
    submissions_total: number;
    submissions_today: number;
    scoring_queue_depth: number;
    active_agents: number;
  };
  recent_audit: AdminAuditEntryDTO[];
}

export interface ScoringStatusDTO {
  scorer: { type: string; version: string };
  counts_by_status: Record<string, number>;
  scored_total: number;
  average_score: number | null;
  distribution: { range: string; count: number }[];
}

export interface AdminAuditPageDTO {
  entries: AdminAuditEntryDTO[];
  total: number;
  page: number;
  per_page: number;
  pages: number;
}

export interface HealthDTO {
  demo_stages?: boolean;
  status: string;
  version: string;
  event_id: string;
  event_state: EventState;
  persistent_storage: boolean;
  db_ok: boolean;
}

export interface UploadDTO {
  id: string;
  submission_id: string;
  path: string;
  url: string;
  mime_type: string;
  size_bytes: number;
  sha256: string;
  effect: ImageEffect;
  created_at: string;
}

export type ApplicationStatus = 'pending' | 'approved' | 'rejected';

export interface ApplicationUserDTO {
  id: string;
  email: string;
  display_name: string | null;
  access_password: string | null;
}

export interface ApplicationDTO {
  id: string;
  name: string;
  email: string;
  team: string | null;
  project_interest: string | null;
  status: ApplicationStatus;
  source: 'form' | 'import';
  user_id: string | null;
  created_at: string;
  decided_at: string | null;
  user: ApplicationUserDTO | null;
}

export interface ApplicationListDTO {
  applications: ApplicationDTO[];
  total: number;
  counts: Record<ApplicationStatus, number>;
}

export interface CsvImportRowDTO {
  application_id: string;
  user_id: string;
  name: string;
  email: string;
  team: string | null;
  access_password: string;
}

export interface CsvImportResultDTO {
  created: CsvImportRowDTO[];
  skipped: { row: number; email: string; reason: string }[];
  errors: { row: number; reason: string }[];
}

export interface AnnouncementDTO {
  id: string;
  title: string;
  body: string;
  visible: boolean;
  created_at: string;
  modified_at: string;
}

export interface RelatedProjectDTO {
  id: string;
  title: string;
  status: string;
  track_id: string | null;
}

export interface RelatedTeamDTO {
  id: string;
  display_name: string;
  role_in_team: string;
}

export interface ParticipantDetailDTO extends ParticipantDTO {
  projects: RelatedProjectDTO[];
  teams: RelatedTeamDTO[];
  members: TeamMemberDTO[];
}

export interface TeamMemberDTO {
  display_name: string;
  role_in_team: string;
  kind: 'human' | 'agent';
}

export interface TeamDTO {
  image?: string | null;
  id: string;
  event_id: string;
  type: string;
  display_name: string;
  affiliation: string | null;
  status: string;
  is_waiting: boolean;
  members: TeamMemberDTO[];
}

export interface AdminUserDTO {
  id: string;
  email: string;
  display_name: string | null;
  role: string;
  status: string;
  access_password: string | null;
  created_at: string;
  last_login_at: string | null;
}

const BASE = '';

const STAGE_NAMES = ['DRAFT', 'OPEN', 'FROZEN', 'FINAL', 'ARCHIVED'];
const STAGE_STORAGE_KEY = 'hackritual:demo_stage';

/** The visitor's chosen demo stage: URL ?stage= wins, then localStorage,
 * then the legacy cookie. Cookies die inside the huggingface.co iframe
 * (third-party, SameSite), so the choice rides as a header on every call. */
export function currentDemoStage(): string | null {
  if (typeof window === 'undefined') return null;
  const m = /[?&]stage=([A-Za-z]+)/.exec(window.location.search);
  if (m && STAGE_NAMES.includes(m[1].toUpperCase())) return m[1].toUpperCase();
  try {
    const stored = window.localStorage.getItem(STAGE_STORAGE_KEY);
    if (stored && STAGE_NAMES.includes(stored)) return stored;
  } catch {
    /* storage unavailable — fall through */
  }
  for (const part of document.cookie.split(';')) {
    const [k, v] = part.trim().split('=');
    if (k === 'demo_stage' && v && STAGE_NAMES.includes(v.toUpperCase())) {
      return v.toUpperCase();
    }
  }
  return null;
}

export function setDemoStage(stage: string | null): void {
  try {
    if (stage) window.localStorage.setItem(STAGE_STORAGE_KEY, stage);
    else window.localStorage.removeItem(STAGE_STORAGE_KEY);
  } catch {
    /* storage unavailable */
  }
  // Cookie kept as a best-effort backup for first-party contexts.
  document.cookie = stage
    ? `demo_stage=${stage}; path=/; max-age=31536000; samesite=lax`
    : 'demo_stage=; path=/; max-age=0';
}

function stageHeaders(): Record<string, string> {
  const stage = currentDemoStage();
  return stage ? { 'x-demo-stage': stage } : {};
}

export async function fetchJson<T>(path: string, fallback: T): Promise<T> {
  try {
    const res = await fetch(`${BASE}${path}`, {
      headers: { accept: 'application/json', ...stageHeaders() },
      credentials: 'include',
    });
    if (!res.ok) return fallback;
    return (await res.json()) as T;
  } catch {
    return fallback;
  }
}

export async function requireJson<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    ...init,
    headers: { accept: 'application/json', ...stageHeaders(), ...(init.headers ?? {}) },
    credentials: 'include',
  });
  if (!res.ok) {
    throw new ApiError(res.status, await res.text().catch(() => ''));
  }
  return (await res.json()) as T;
}

/** DELETE that expects 204 — shares the stage header and error semantics. */
async function deleteVoid(path: string): Promise<void> {
  const res = await fetch(`${BASE}${path}`, {
    method: 'DELETE',
    headers: stageHeaders(),
    credentials: 'include',
  });
  if (!res.ok) throw new ApiError(res.status, await res.text().catch(() => ''));
}

let _backendPresent: Promise<boolean> | null = null;

/** True when a real backend answers /api/health (memoized for the page load).
 * Pages must render API data — even empty lists — whenever this is true;
 * the stage mocks are reserved for the backend-less static demo. */
export function backendPresent(): Promise<boolean> {
  if (_backendPresent === null) {
    _backendPresent = fetch(`${BASE}/api/health`, {
      headers: { accept: 'application/json', ...stageHeaders() },
      credentials: 'include',
    })
      .then(async (res) => {
        if (!res.ok) return false;
        const h = (await res.json()) as HealthDTO;
        return h.db_ok === true && h.event_id !== 'demo';
      })
      .catch(() => false);
  }
  return _backendPresent;
}

export class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`api ${status}: ${body || '(no body)'}`);
  }
}

/* ───────────────────────────────────────────────────────────── *
 * Typed endpoints                                                 *
 * ───────────────────────────────────────────────────────────── */

export const api = {
  health: () =>
    fetchJson<HealthDTO>('/api/health', {
      status: 'ok',
      version: '0.1.0',
      event_id: 'demo',
      event_state: 'OPEN',
      persistent_storage: false,
      db_ok: true,
    }),

  event: () => fetchJson<EventDTO | null>('/api/event', null),

  leaderboard: (track?: string, limit = 50) =>
    fetchJson<LeaderboardDTO>(
      '/api/leaderboard?limit=' +
        limit +
        (track ? `&track=${encodeURIComponent(track)}` : ''),
      {
        event_id: '',
        event_state: 'OPEN',
        leaderboard_mode: 'best',
        entries: [],
      },
    ),

  tracks: () => fetchJson<TrackDTO[]>('/api/tracks', []),
  phases: () => fetchJson<PhaseDTO[]>('/api/phases', []),
  pages: () => fetchJson<PageDTO[]>('/api/pages', []),

  // ── admin content CRUD (tracks / phases / pages)
  createTrack: (input: { name: string; description?: string | null }) =>
    requireJson<TrackDTO>('/api/tracks', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  updateTrack: (id: string, input: { name?: string; description?: string | null }) =>
    requireJson<TrackDTO>(`/api/tracks/${id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  deleteTrack: async (id: string) => {
    await deleteVoid(`/api/tracks/${id}`);
  },

  createPhase: (input: {
    name: string;
    description?: string | null;
    starts_at?: string | null;
    ends_at?: string | null;
  }) =>
    requireJson<PhaseDTO>('/api/phases', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  updatePhase: (
    id: string,
    input: {
      name?: string;
      description?: string | null;
      starts_at?: string | null;
      ends_at?: string | null;
    },
  ) =>
    requireJson<PhaseDTO>(`/api/phases/${id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  deletePhase: async (id: string) => {
    await deleteVoid(`/api/phases/${id}`);
  },

  createPage: (input: {
    title: string;
    content: string;
    visible?: boolean;
    order?: number;
    phase_id?: string | null;
  }) =>
    requireJson<PageDTO>('/api/pages', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  updatePage: (
    id: string,
    input: {
      title?: string;
      content?: string;
      visible?: boolean;
      order?: number;
      phase_id?: string | null;
    },
  ) =>
    requireJson<PageDTO>(`/api/pages/${id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  deletePage: async (id: string) => {
    await deleteVoid(`/api/pages/${id}`);
  },

  projects: (track?: string) =>
    fetchJson<ProjectDTO[]>(
      '/api/projects' + (track ? `?track_id=${encodeURIComponent(track)}` : ''),
      [],
    ),
  project: (id: string) => fetchJson<ProjectDTO | null>(`/api/projects/${id}`, null),

  submissions: (projectId?: string) =>
    fetchJson<SubmissionDTO[]>(
      '/api/submissions' + (projectId ? `?project_id=${encodeURIComponent(projectId)}` : ''),
      [],
    ),

  participants: async (): Promise<ParticipantDTO[]> => {
    // /api/participants is paginated: { participants, total, page, per_page, pages }
    const wrapped = await fetchJson<{ participants?: ParticipantDTO[] }>(
      '/api/participants?per_page=100',
      { participants: [] },
    );
    return Array.isArray(wrapped.participants) ? wrapped.participants : [];
  },

  // ── auth (form callers throw on failure)
  login: (password: string) =>
    requireJson<{ user: { id: string; email: string; role: string } }>(
      '/api/auth/login',
      {
        method: 'POST',
        headers: { 'content-type': 'application/json' },
        body: JSON.stringify({ password }),
      },
    ),

  // ── applications (the petition desk)
  submitApplication: (input: {
    name: string;
    email: string;
    team?: string;
    project_interest?: string;
  }) =>
    requireJson<{ id: string; status: string }>('/api/applications', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  // Public team roster — members by display name, no emails or invite codes.
  teams: () => fetchJson<TeamDTO[]>('/api/teams', []),

  createTeam: (input: { display_name: string; affiliation?: string; links?: string[] }) =>
    requireJson<{ id: string; display_name: string; invite_code: string }>('/api/teams', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  // Enlist an agent into a team — caller must be on the team and own the
  // agent (the keeper may enlist anywhere).
  enlistAgent: (teamId: string, agentId: string) =>
    requireJson<{ status: string; member_id: string }>(`/api/teams/${teamId}/agents`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ agent_id: agentId }),
    }),

  // ── announcements (dispatches under the hero)
  announcements: () =>
    fetchJson<AnnouncementDTO[]>('/api/announcements', []),

  adminAnnouncements: () =>
    requireJson<AnnouncementDTO[]>('/api/admin/announcements'),

  createAnnouncement: (input: { title: string; body: string; visible?: boolean }) =>
    requireJson<AnnouncementDTO>('/api/admin/announcements', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  updateAnnouncement: (
    id: string,
    input: { title?: string; body?: string; visible?: boolean },
  ) =>
    requireJson<AnnouncementDTO>(`/api/admin/announcements/${id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  deleteAnnouncement: async (id: string) => {
    await deleteVoid(`/api/admin/announcements/${id}`);
  },

  adminApplications: (status?: ApplicationStatus) =>
    requireJson<ApplicationListDTO>(
      `/api/admin/applications${status ? `?status=${status}` : ''}`,
    ),

  approveApplication: (id: string) =>
    requireJson<ApplicationDTO>(`/api/admin/applications/${id}/approve`, {
      method: 'POST',
    }),

  rejectApplication: (id: string) =>
    requireJson<ApplicationDTO>(`/api/admin/applications/${id}/reject`, {
      method: 'POST',
    }),

  importUsersCsv: (file: File) => {
    const form = new FormData();
    form.append('file', file);
    return requireJson<CsvImportResultDTO>('/api/admin/users/import-csv', {
      method: 'POST',
      body: form,
    });
  },

  regeneratePassword: (userId: string) =>
    requireJson<AdminUserDTO>(`/api/admin/users/${userId}/regenerate-password`, {
      method: 'POST',
    }),

  me: () =>
    fetchJson<MeDTO | null>('/api/auth/me', null),

  uploadPortrait: async (
    file: File,
    effect: ImageEffect,
    contrast: number,
    brightness: number,
    scale: number,
  ) => {
    const form = new FormData();
    form.append('file', file);
    form.append('effect', effect);
    form.append('contrast', String(contrast));
    form.append('brightness', String(brightness));
    form.append('scale', String(scale));
    return requireJson<MeDTO>('/api/me/portrait', { method: 'POST', body: form });
  },

  retunePortrait: async (
    effect: ImageEffect,
    contrast: number,
    brightness: number,
    scale: number,
  ) => {
    const form = new FormData();
    form.append('effect', effect);
    form.append('contrast', String(contrast));
    form.append('brightness', String(brightness));
    form.append('scale', String(scale));
    return requireJson<MeDTO>('/api/me/portrait', { method: 'PATCH', body: form });
  },

  deletePortrait: () =>
    requireJson<MeDTO>('/api/me/portrait', { method: 'DELETE' }),

  // ── agents ──
  agents: () => fetchJson<AgentDTO[]>('/api/agents', []),

  createAgent: (name: string) =>
    requireJson<AgentCreatedDTO>('/api/agents', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ name }),
    }),

  rotateAgent: (id: string) =>
    requireJson<AgentCreatedDTO>(`/api/agents/${id}/rotate`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
    }),

  revokeAgent: (id: string) =>
    requireJson<AgentDTO>(`/api/agents/${id}/revoke`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
    }),

  deleteAgent: async (id: string) => {
    await deleteVoid(`/api/agents/${id}`);
  },

  // ── admin
  seedDemoData: () =>
    requireJson<Record<string, number>>('/api/admin/seed', { method: 'POST' }),

  // Advance the event state machine. `confirm` is required for the
  // FROZEN→OPEN reopen; the backend rejects it otherwise.
  transitionState: (state: EventState, reason?: string, confirm = false) =>
    requireJson<StateTransitionDTO>('/api/admin/event/state', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ state, reason, confirm }),
    }),

  // Edit the event's identity — title, type, dates. The env vars only seed
  // these on first boot; the panel owns them afterwards.
  updateEventMeta: (input: {
    title?: string;
    type?: string;
    start?: string;
    end?: string;
  }) =>
    requireJson<EventDTO>('/api/admin/event/meta', {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(input),
    }),

  // ── admin console roll-ups (require_admin; null in demo / non-admin) ──
  // Server-authoritative aggregations. Returns null when the dedicated
  // endpoint is unreachable or the session isn't an admin, so callers can fall
  // back to client-side counts (demo mode) without throwing.
  adminDashboard: () => fetchJson<AdminDashboardDTO | null>('/api/admin/dashboard', null),

  adminScoringStatus: () =>
    fetchJson<ScoringStatusDTO | null>('/api/admin/scoring/status', null),

  adminAudit: (params: {
    action?: string;
    actor?: string;
    since_hours?: number;
    page?: number;
    per_page?: number;
  } = {}) => {
    const qs = new URLSearchParams();
    if (params.action) qs.set('action', params.action);
    if (params.actor) qs.set('actor', params.actor);
    if (params.since_hours) qs.set('since_hours', String(params.since_hours));
    if (params.page) qs.set('page', String(params.page));
    if (params.per_page) qs.set('per_page', String(params.per_page));
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return fetchJson<AdminAuditPageDTO | null>(`/api/admin/audit${suffix}`, null);
  },

  // ── repositories
  projectRepos: async (projectId: string) => {
    const res = await fetchJson<
      { can_edit: boolean; repositories: RepoDTO[] } | RepoDTO[]
    >(`/api/projects/${projectId}/repos`, { can_edit: false, repositories: [] });
    // Older backends returned a bare array.
    return Array.isArray(res) ? { can_edit: false, repositories: res } : res;
  },

  attachRepo: (projectId: string, url: string, label?: string) =>
    requireJson<RepoDTO>(`/api/projects/${projectId}/repos`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ url, label }),
    }),

  refreshRepo: (projectId: string, repoId: string) =>
    requireJson<RepoDTO>(`/api/projects/${projectId}/repos/${repoId}/refresh`, {
      method: 'POST',
    }),

  detachRepo: async (projectId: string, repoId: string) => {
    await deleteVoid(`/api/projects/${projectId}/repos/${repoId}`);
  },

  participantFeed: (participantId: string) =>
    fetchJson<CommitDTO[]>(`/api/feed/participant/${participantId}`, []),

  // ── audit log
  logPage: (params: {
    limit?: number;
    offset?: number;
    action_prefix?: string;
    actor?: string;
    target_type?: string;
  } = {}) => {
    const qs = new URLSearchParams();
    if (params.limit) qs.set('limit', String(params.limit));
    if (params.offset) qs.set('offset', String(params.offset));
    if (params.action_prefix) qs.set('action_prefix', params.action_prefix);
    if (params.actor) qs.set('actor', params.actor);
    if (params.target_type) qs.set('target_type', params.target_type);
    const suffix = qs.toString() ? `?${qs.toString()}` : '';
    return fetchJson<LogPageDTO>(`/api/log${suffix}`, {
      entries: [],
      total: 0,
      limit: params.limit ?? 50,
      offset: params.offset ?? 0,
    });
  },

  // ── single submission
  submission: (id: string) =>
    fetchJson<SubmissionDTO | null>(`/api/submissions/${id}`, null),

  updateSubmission: (
    id: string,
    patch: {
      title?: string;
      description?: string;
      result?: string;
      payload_json?: string;
      status?: SubmissionStatus;
    },
  ) =>
    requireJson<SubmissionDTO>(`/api/submissions/${id}`, {
      method: 'PATCH',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(patch),
    }),

  createSubmission: (body: {
    project_id: string;
    participant_id: string;
    title?: string;
    description?: string;
    result?: string;
    payload_json?: string;
  }) =>
    requireJson<SubmissionDTO>('/api/submissions', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }),

  // ── scoring
  listScores: (submissionId: string) =>
    fetchJson<ScoreDTO[]>(`/api/submissions/${submissionId}/scores`, []),

  createScore: (
    submissionId: string,
    body: { score_value?: number; breakdown?: Record<string, number>; notes?: string },
  ) =>
    requireJson<ScoreDTO>(`/api/submissions/${submissionId}/scores`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }),

  deleteScore: async (scoreId: string) => {
    await deleteVoid(`/api/scores/${scoreId}`);
  },

  logout: async () => {
    try {
      await fetch('/api/auth/logout', {
        method: 'POST',
        credentials: 'include',
        headers: stageHeaders(),
      });
    } catch {
      /* swallow — we'll reload anyway */
    }
  },

  // ── mutations used by forms
  createProject: (body: {
    title: string;
    description: string;
    track_id?: string;
    image?: string;
    proposed_by_participant_id: string;
  }) =>
    requireJson<ProjectDTO>('/api/projects', {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(body),
    }),

  uploadImage: async (
    file: File,
    submissionId: string,
    participantId: string,
    effect: ImageEffect,
  ) => {
    const form = new FormData();
    form.append('file', file);
    form.append('submission_id', submissionId);
    form.append('participant_id', participantId);
    form.append('effect', effect);
    return requireJson<UploadDTO>('/api/uploads', {
      method: 'POST',
      body: form,
    });
  },
};
