/**
 * Mock datasets — one per ritual state.
 *
 * Each stage has its own voice. The ritual log in particular tells a
 * narrative when you scrub through DRAFT → OPEN → FROZEN → FINAL → ARCHIVED:
 *   DRAFT      whispers — the circle being drawn, seats reserved
 *   OPEN       clatter — proposals, joinings, the forge running hot
 *   FROZEN     hush — gates closed, judges convening
 *   FINAL      procession — winners declared, glow returns
 *   ARCHIVED   silence — the record sealed, export ready
 */

export type EventState = 'DRAFT' | 'OPEN' | 'FROZEN' | 'FINAL' | 'ARCHIVED';
export const STATES: EventState[] = ['DRAFT', 'OPEN', 'FROZEN', 'FINAL', 'ARCHIVED'];

export type ImageVariant = 'bloom' | 'nucleus' | 'sprout' | 'lattice';

export interface PhaseMock {
  name: string;
  glyph: string;
  range: string;
  epigraph: string;
  status: 'completed' | 'active' | 'upcoming';
}

export interface ProposalMock {
  id: number;
  title: string;
  track: string;
  blurb: string;
  body?: string;
  proposer: string;
  team?: string;
  rank?: number;
  score?: number;
  versions?: number;
  imageVariant?: ImageVariant;
}

export interface ParticipantMock {
  handle: string;
  displayName?: string;
  kind: 'human' | 'agent' | 'team';
  meta: string;
  affiliation?: string;
  waitlist?: boolean;
  joinedAt?: string;
  bio?: string;
  imageVariant?: ImageVariant;
}

export interface TeamMock {
  handle: string;
  name: string;
  blurb: string;
  members: { handle: string; kind: 'human' | 'agent'; role: 'captain' | 'member' }[];
  project?: string;
  trackHint?: string;
  imageVariant?: ImageVariant;
}

export interface SubmissionMock {
  id: number;
  projectId: number;
  projectTitle: string;
  team: string;
  version: number;
  status: 'draft' | 'final' | 'withdrawn';
  result?: string;
  modifiedAt: string;
  score?: number;
}

export interface TrackMock {
  name: string;
  count: number;
  glyph: string;
  blurb: string;
}

export interface LogEntry {
  ts: string;
  actor: string;
  verb: string;
  object?: string;
  tone?: 'normal' | 'primary' | 'warm' | 'accent';
}

export interface CmsPage {
  slug: string;
  title: string;
  blurb: string;
  body: string[];
}

export interface StageData {
  state: EventState;
  hero: {
    eyebrowCall: string;
    titleTop: string;
    titleBottom: string;
    titleAccent: 'primary' | 'warm' | 'accent' | 'muted';
    flicker: boolean;
    primaryCta: { label: string; href: string };
    secondaryCta: { label: string; href: string };
    epigraph: string;
    countdown?: { label: string; secondsAhead: number };
  };
  phases: PhaseMock[];
  proposals: ProposalMock[];
  proposalsHeading: string;
  proposalsSeeAll: { label: string; href: string };
  participants: ParticipantMock[];
  participantsHeading: string;
  participantCount: number;
  waitlistCount: number;
  tracks: TrackMock[];
  teams: TeamMock[];
  submissions: SubmissionMock[];
  ritualLog: LogEntry[];
  winners?: ProposalMock[];
  botanical: string;
  /** "Your" page context — the perspective of the logged-in user. */
  you?: {
    handle: string;
    teamName?: string;
    projectId?: number;
    projectTitle?: string;
    projectStatus?: string;
    nextAction?: { label: string; href: string };
    deadline?: string;
  };
}

/* ───────────────────────────────────────────────────────────── *
 * ASCII botanicals — one per stage, telling the same story.       *
 * ───────────────────────────────────────────────────────────── */

const BOTANICAL_SEED = `        .
        .
       ( )
      (   )
     ( ◇   )
      (   )
       ( )
        '
   ━━━ . ━━━`;

const BOTANICAL_SPROUT = `        .  ,
         \\ /
         \\|/
       __/|\\__
        / | \\
       /  |  \\
      |   ◆   |
      |   |   |
   ───┴───┴───┴───
       ╲ │ ╱
        ╲│╱
   ━━━━━ ◆ ━━━━━`;

const BOTANICAL_BLOOM = `       \\ | /
        \\|/
      __ ✦ __
       /|◆|\\
        \\|/
         |
         |
         |
   ━━━━━ ◆ ━━━━━
       ╲ │ ╱
       ╲ │ ╱
   ━━━━━ ✦ ━━━━━`;

const BOTANICAL_FRUIT = `      _____
     /     \\
    /       \\
   |   ◆◆◆   |
    \\  ◆◆◆  /
     \\_____/
        |
        |
   ╲━━━━┼━━━━╱
        |
        |
   ━━━━━◆━━━━━`;

const BOTANICAL_DRIED = `        '
        '
       ' '
      '   '
     '  ◇  '
      '   '
       ' '
        '
   ┄┄┄ . ┄┄┄
   pressed   `;

/* ───────────────────────────────────────────────────────────── *
 * Reusable building blocks                                        *
 * ───────────────────────────────────────────────────────────── */

const TRACKS_OPEN: TrackMock[] = [
  {
    name: 'data-science',
    count: 9,
    glyph: '◆',
    blurb:
      'datasets, models, and the geometry between them. work that looks like graphs and reasoning.',
  },
  {
    name: 'research-infra',
    count: 7,
    glyph: '◇',
    blurb:
      'the rails. schedulers, storage, observability. how science holds itself up.',
  },
  {
    name: 'small-tools',
    count: 3,
    glyph: '▰',
    blurb: 'one-file utilities. cli rituals. things that compose well.',
  },
];

const TRACKS_DRAFT: TrackMock[] = TRACKS_OPEN.map((t) => ({ ...t, count: 0 }));

const PARTICIPANTS_OPEN: ParticipantMock[] = [
  {
    handle: 'ada.cole',
    displayName: 'Ada Cole',
    kind: 'human',
    meta: 'MIT · data-science',
    affiliation: 'MIT',
    joinedAt: '2026-05-13 14:32',
    bio: 'designs models that try to know when they should stop talking. submits drafts at 4 a.m.',
    imageVariant: 'sprout',
  },
  {
    handle: 'marrowbot',
    displayName: 'marrowbot v3.2',
    kind: 'agent',
    meta: 'solo · key …a4f2',
    affiliation: 'owned by jun.k',
    joinedAt: '2026-05-13 14:29',
    bio: 'a small constraint solver that prefers ascii output. politely declines to score itself.',
    imageVariant: 'lattice',
  },
  {
    handle: 'the_owls',
    displayName: 'the_owls',
    kind: 'team',
    meta: '4 members · captain: jun.k',
    affiliation: 'Lisbon collective',
    joinedAt: '2026-05-13 14:24',
    bio: 'nocturnal. four humans, two agents. shared a single keyboard last year. won.',
    imageVariant: 'nucleus',
  },
  {
    handle: 'weft',
    displayName: 'weft',
    kind: 'agent',
    meta: 'captained by the_owls',
    affiliation: 'agent',
    joinedAt: '2026-05-13 14:30',
    bio: 'an LLM-and-bash sketchpad. participates in teams; never alone.',
    imageVariant: 'lattice',
  },
  {
    handle: 'jun.k',
    displayName: 'June K.',
    kind: 'human',
    meta: 'self-employed · small-tools',
    affiliation: 'Seoul',
    joinedAt: '2026-05-13 14:18',
    bio: 'writes the kind of cli that asks you a question and then waits, patiently.',
    imageVariant: 'sprout',
  },
  {
    handle: 'photosym',
    displayName: 'Photosym',
    kind: 'human',
    meta: 'CERN · research-infra',
    affiliation: 'CERN',
    joinedAt: '2026-05-13 13:55',
    bio: 'thinks scheduling is a form of music. has opinions about cron.',
    imageVariant: 'sprout',
  },
  {
    handle: 'jane.tu',
    displayName: 'Jane Tu',
    kind: 'human',
    meta: 'waitlist · small-tools',
    affiliation: 'NYU',
    joinedAt: '2026-05-13 14:50',
    waitlist: true,
    bio: 'queue is fine. the queue is part of the ritual.',
    imageVariant: 'sprout',
  },
  {
    handle: 'rendermouse',
    displayName: 'rendermouse',
    kind: 'agent',
    meta: 'waitlist · solo',
    affiliation: 'agent',
    joinedAt: '2026-05-13 14:51',
    waitlist: true,
    bio: 'graphics-only. produces postscript when asked anything.',
    imageVariant: 'lattice',
  },
];

const TEAMS_OPEN: TeamMock[] = [
  {
    handle: 'the_owls',
    name: 'the_owls',
    blurb:
      'A Lisbon collective. Four humans plus two agents. Speaks in soft voices and ships violently.',
    members: [
      { handle: 'jun.k', kind: 'human', role: 'captain' },
      { handle: 'ada.cole', kind: 'human', role: 'member' },
      { handle: 'weft', kind: 'agent', role: 'member' },
      { handle: 'marrowbot', kind: 'agent', role: 'member' },
    ],
    project: 'mycelium-mesh',
    trackHint: 'data-science',
    imageVariant: 'nucleus',
  },
  {
    handle: 'photosym',
    name: 'photosym',
    blurb: 'A duo working on circadian scheduling. Trades sleep for solar curves.',
    members: [
      { handle: 'photosym', kind: 'human', role: 'captain' },
      { handle: 'rendermouse', kind: 'agent', role: 'member' },
    ],
    project: 'photosym-os',
    trackHint: 'research-infra',
    imageVariant: 'nucleus',
  },
  {
    handle: 'meadow_solo',
    name: 'meadow',
    blurb: 'Solo team. One human, one keyboard, one good idea.',
    members: [{ handle: 'jun.k', kind: 'human', role: 'captain' }],
    project: 'the_meadow_ide',
    trackHint: 'small-tools',
    imageVariant: 'sprout',
  },
];

const SUBMISSIONS_OPEN: SubmissionMock[] = [
  {
    id: 1,
    projectId: 3,
    projectTitle: 'mycelium-mesh',
    team: 'the_owls',
    version: 2,
    status: 'draft',
    result: '',
    modifiedAt: '2026-05-14 13:48',
  },
  {
    id: 2,
    projectId: 3,
    projectTitle: 'mycelium-mesh',
    team: 'the_owls',
    version: 1,
    status: 'draft',
    result: 'WIP repo + readme',
    modifiedAt: '2026-05-14 11:02',
  },
  {
    id: 3,
    projectId: 2,
    projectTitle: 'photosym-os',
    team: 'photosym',
    version: 1,
    status: 'draft',
    result: '',
    modifiedAt: '2026-05-14 12:14',
  },
  {
    id: 4,
    projectId: 7,
    projectTitle: 'lichen-loom',
    team: 'weft',
    version: 1,
    status: 'draft',
    result: 'weather-feed adapter · first weave',
    modifiedAt: '2026-05-14 12:40',
  },
  {
    id: 5,
    projectId: 4,
    projectTitle: 'spore-print',
    team: 'marrowbot',
    version: 1,
    status: 'draft',
    result: 'automata bank · seed generator',
    modifiedAt: '2026-05-14 13:05',
  },
  {
    id: 6,
    projectId: 1,
    projectTitle: 'the_meadow_ide',
    team: 'meadow',
    version: 2,
    status: 'draft',
    result: 'audio-engine prototype · 1 plate',
    modifiedAt: '2026-05-14 13:21',
  },
];

const SUBMISSIONS_FROZEN: SubmissionMock[] = [
  {
    id: 10,
    projectId: 3,
    projectTitle: 'mycelium-mesh',
    team: 'the_owls',
    version: 3,
    status: 'final',
    result: 'demo.mp4 · report.pdf · github.com/the-owls/mycelium-mesh',
    modifiedAt: '2026-05-16 11:58',
  },
  {
    id: 11,
    projectId: 7,
    projectTitle: 'lichen-loom',
    team: 'weft',
    version: 2,
    status: 'final',
    result: 'demo · poster.pdf',
    modifiedAt: '2026-05-16 11:54',
  },
  {
    id: 12,
    projectId: 2,
    projectTitle: 'photosym-os',
    team: 'photosym',
    version: 1,
    status: 'final',
    result: 'paper.pdf · slides',
    modifiedAt: '2026-05-16 11:30',
  },
];

const SUBMISSIONS_FINAL: SubmissionMock[] = SUBMISSIONS_FROZEN.map((s) => ({
  ...s,
  score: s.team === 'the_owls' ? 94.2 : s.team === 'weft' ? 89.8 : 87.1,
}));

const PHASES_OPEN: PhaseMock[] = [
  {
    name: 'Ideation',
    glyph: '◇',
    range: 'May 14 · 09:00 – 18:00',
    epigraph: 'the seeds settle into soil.',
    status: 'completed',
  },
  {
    name: 'Hacking',
    glyph: '◆',
    range: 'May 14 · 18:00 – May 16 · 12:00',
    epigraph: 'the forge runs hot.',
    status: 'active',
  },
  {
    name: 'Judging',
    glyph: '▢',
    range: 'May 16 · 12:00 – 18:00',
    epigraph: 'the verdict is sown.',
    status: 'upcoming',
  },
];

/* ───────────────────────────────────────────────────────────── *
 * Datasets                                                        *
 * ───────────────────────────────────────────────────────────── */

const DRAFT: StageData = {
  state: 'DRAFT',
  hero: {
    eyebrowCall: "ritual.draft('the_circle')",
    titleTop: 'A Forge to Come:',
    titleBottom: 'Light-and-Lichen',
    titleAccent: 'muted',
    flicker: false,
    primaryCta: { label: 'petition to join', href: '/apply/' },
    secondaryCta: { label: 'read the rites', href: '/pages/rites/' },
    epigraph:
      'The circle is being drawn. No participants yet — soon, the gates will open and the forge will run.',
    countdown: { label: 'gates open in', secondsAhead: 3 * 86400 + 5 * 3600 + 12 * 60 },
  },
  phases: PHASES_OPEN.map((p) => ({ ...p, status: 'upcoming', epigraph: p.epigraph.replace(/(settle|run|sown)/, (m) => ({ settle: 'will settle', run: 'will run', sown: 'will be sown' }[m] ?? m)) })),
  proposals: [],
  proposalsHeading: 'no proposals yet',
  proposalsSeeAll: { label: 'see the tracks ↗', href: '/projects/' },
  participants: [
    { handle: 'tomas.k', displayName: 'Tomas K.', kind: 'human', meta: 'organiser', joinedAt: '2026-05-10 09:14' },
    { handle: 'ada.cole', displayName: 'Ada Cole', kind: 'human', meta: 'reserved · waitlist', joinedAt: '2026-05-13 09:42', waitlist: true, imageVariant: 'sprout' },
    { handle: 'jun.k', displayName: 'June K.', kind: 'human', meta: 'reserved · waitlist', joinedAt: '2026-05-13 09:48', waitlist: true, imageVariant: 'sprout' },
    { handle: 'photosym', displayName: 'Photosym', kind: 'human', meta: 'reserved · waitlist', joinedAt: '2026-05-13 09:53', waitlist: true, imageVariant: 'sprout' },
    { handle: 'jane.tu', displayName: 'Jane Tu', kind: 'human', meta: 'reserved · waitlist', joinedAt: '2026-05-13 09:57', waitlist: true, imageVariant: 'sprout' },
  ],
  participantsHeading: 'who is waiting',
  participantCount: 0,
  waitlistCount: 4,
  tracks: TRACKS_DRAFT,
  teams: [],
  submissions: [],
  ritualLog: [
    { ts: '09:14:02', actor: 'system', verb: 'the circle is drawn', tone: 'primary' },
    { ts: '09:15:31', actor: 'tomas.k', verb: 'inscribed the tracks', object: 'data-science · research-infra · small-tools' },
    { ts: '09:16:12', actor: 'tomas.k', verb: 'bound the rules', object: 'submission cap 3 / 24h' },
    { ts: '09:18:00', actor: 'tomas.k', verb: 'set ideation to', object: 'May 14 09:00' },
    { ts: '09:18:41', actor: 'tomas.k', verb: 'set the scorer to', object: 'default-1.0' },
    { ts: '09:25:00', actor: 'system', verb: 'petition desk opened', tone: 'primary' },
    { ts: '09:42:11', actor: 'ada.cole', verb: 'reserved a seat (waitlist)', tone: 'warm' },
    { ts: '09:48:55', actor: 'jun.k', verb: 'reserved a seat (waitlist)', tone: 'warm' },
    { ts: '09:53:20', actor: 'photosym', verb: 'reserved a seat (waitlist)', tone: 'warm' },
    { ts: '09:57:44', actor: 'jane.tu', verb: 'reserved a seat (waitlist)', tone: 'warm' },
    { ts: '10:01:00', actor: 'tomas.k', verb: 'published the rites' },
    { ts: '10:02:18', actor: 'system', verb: 'awaiting the appointed hour' },
  ],
  botanical: BOTANICAL_SEED,
  you: {
    handle: 'you',
    nextAction: { label: 'reserve a seat', href: '/signin/' },
    deadline: 'gates open in 3d 05h',
  },
};

const PROPOSAL_LICHEN: ProposalMock = {
  id: 7,
  title: 'lichen-loom',
  track: 'small-tools',
  blurb: 'a weave of cron jobs that schedule themselves around weather.',
  body:
    'A scheduler that listens to weather feeds and decides when to run. Rain delays the backups; sun brings the batch jobs forward. The loom held through a simulated storm week without dropping a thread.',
  proposer: 'weft',
  team: 'weft',
  versions: 2,
  imageVariant: 'lattice',
};

const PROPOSALS_OPEN: ProposalMock[] = [
  {
    id: 3,
    title: 'mycelium-mesh',
    track: 'data-science',
    blurb: 'gossip protocols modeled on fungal nutrient routing, over IPFS.',
    body:
      'A peer-to-peer protocol that treats each node like a hyphal tip — extending toward what it needs, pulling back from what it does not. Routing decisions are local, gossip-based, and emerge from concentration gradients rather than topology tables.',
    proposer: 'the_owls',
    team: 'the_owls',
    versions: 2,
    imageVariant: 'nucleus',
  },
  {
    id: 2,
    title: 'photosym-os',
    track: 'research-infra',
    blurb: 'a circadian scheduler — workloads track sunlight on the grid.',
    body:
      'Most workloads do not care when they run. The grid does. photosym-os is a scheduler that asks the grid where the sun currently is and queues batch jobs accordingly.',
    proposer: 'photosym',
    team: 'photosym',
    versions: 1,
    imageVariant: 'bloom',
  },
  {
    id: 1,
    title: 'the_meadow_ide',
    track: 'small-tools',
    blurb: 'an IDE that breathes. ambient sound shifts with build state.',
    body:
      'A code editor that produces nothing visible until you start to type. Build pass: birdsong. Build fail: distant rain. Test green: leaves rustling. Test red: silence. You learn to feel the state of your program.',
    proposer: 'jun.k',
    team: 'meadow',
    versions: 3,
    imageVariant: 'sprout',
  },
  PROPOSAL_LICHEN,
  {
    id: 4,
    title: 'spore-print',
    track: 'data-science',
    blurb: 'embed any dataset as a hash of cellular automata states.',
    body:
      'Run a dataset through a bank of cellular automata and keep the diversity profile of the states it produces. Two datasets with the same print are related; the print itself fits in a tweet.',
    proposer: 'marrowbot',
    versions: 1,
    imageVariant: 'lattice',
  },
  {
    id: 5,
    title: 'kombu-cache',
    track: 'research-infra',
    blurb: 'an l4 cache with vegetal eviction policies. lru with fermentation.',
    body:
      'Entries do not expire — they ferment. Frequently read entries stay crisp; neglected ones soften, compress, and eventually compost into bloom filters that remember only that something was once there.',
    proposer: 'ada.cole',
    versions: 1,
    imageVariant: 'nucleus',
  },
  {
    id: 6,
    title: 'burrow.cli',
    track: 'small-tools',
    blurb: 'filesystem navigation that learns from how you move through ground.',
    body:
      'A cd replacement that watches which directories you visit after which, and digs shortcuts. The more you work, the shorter the tunnels. Forgets gracefully when projects end.',
    proposer: 'jun.k',
    versions: 2,
    imageVariant: 'sprout',
  },
  {
    id: 8,
    title: 'petal-fetch',
    track: 'small-tools',
    blurb: 'an http client that flowers in the terminal.',
    body:
      'Each response renders as a different bloom: status codes choose the species, latency sets the stem length, headers become leaves. Slow APIs grow sad, drooping things. You will fix them.',
    proposer: 'jane.tu',
    versions: 1,
    imageVariant: 'bloom',
  },
];

const OPEN: StageData = {
  state: 'OPEN',
  hero: {
    eyebrowCall: "ritual.summon('the_circle')",
    titleTop: 'The Forge of',
    titleBottom: 'Light-and-Lichen',
    titleAccent: 'primary',
    flicker: true,
    primaryCta: { label: 'step into the circle', href: '/signin/' },
    secondaryCta: { label: 'read the rites', href: '/pages/rites/' },
    epigraph:
      'Gather your participants. Forge something from nothing. Export the artefact. Dispel the container.',
    countdown: { label: 'forge closes in', secondsAhead: 32 * 3600 + 14 * 60 + 8 },
  },
  phases: PHASES_OPEN,
  proposals: PROPOSALS_OPEN,
  proposalsHeading: 'latest proposals',
  proposalsSeeAll: { label: 'see all 16 →', href: '/projects/' },
  participants: PARTICIPANTS_OPEN,
  participantsHeading: 'newest into the circle',
  participantCount: 42,
  waitlistCount: 12,
  tracks: TRACKS_OPEN,
  teams: TEAMS_OPEN,
  submissions: SUBMISSIONS_OPEN,
  ritualLog: [
    { ts: '14:32:08', actor: 'ada.cole', verb: 'stepped into the circle' },
    { ts: '14:31:55', actor: 'the_owls', verb: 'forged', object: '#003 mycelium-mesh', tone: 'primary' },
    { ts: '14:31:20', actor: 'jane.tu', verb: 'proposed', object: '#008 petal-fetch' },
    { ts: '14:30:11', actor: 'system', verb: 'the forge is open', tone: 'primary' },
    { ts: '14:29:40', actor: 'marrowbot', verb: 'offered v1 of', object: '#004 spore-print' },
    { ts: '14:29:02', actor: 'marrowbot', verb: 'joined as agent', tone: 'warm' },
    { ts: '14:28:44', actor: 'the_owls', verb: 'invited weft to the team' },
    { ts: '14:27:51', actor: 'weft', verb: 'offered v1 of', object: '#007 lichen-loom' },
    { ts: '14:26:30', actor: 'photosym-os', verb: 'submitted v2 of', object: '#002' },
    { ts: '14:25:48', actor: 'jun.k', verb: 'withdrew v1 of', object: '#001 the_meadow_ide', tone: 'warm' },
    { ts: '14:24:11', actor: 'system', verb: 'phase ideation closed' },
    { ts: '14:22:03', actor: 'ada.cole', verb: 'proposed', object: '#005 kombu-cache' },
    { ts: '14:20:17', actor: 'jun.k', verb: 'proposed', object: '#006 burrow.cli' },
    { ts: '14:18:55', actor: 'jun.k', verb: 'stepped into the circle' },
    { ts: '14:16:02', actor: 'system', verb: 'the gates opened', tone: 'primary' },
  ],
  botanical: BOTANICAL_SPROUT,
  you: {
    handle: 'ada.cole',
    teamName: 'the_owls',
    projectId: 3,
    projectTitle: 'mycelium-mesh',
    projectStatus: 'approved · drafting v2',
    nextAction: { label: 'finalise submission', href: '/submissions/' },
    deadline: 'forge closes in 32h 14m',
  },
};

const FROZEN: StageData = {
  state: 'FROZEN',
  hero: {
    eyebrowCall: "ritual.seal('the_forge')",
    titleTop: 'The Forge Cools at',
    titleBottom: 'Light-and-Lichen',
    titleAccent: 'warm',
    flicker: false,
    primaryCta: { label: 'watch the judging', href: '/timeline/' },
    secondaryCta: { label: 'review submissions', href: '/submissions/' },
    epigraph:
      'Submissions are sealed. The judges have convened. Within hours, the verdict will be inscribed.',
    countdown: { label: 'verdict in', secondsAhead: 4 * 3600 + 8 * 60 },
  },
  phases: [
    { ...PHASES_OPEN[0], epigraph: 'the seeds settled into soil.' },
    { ...PHASES_OPEN[1], status: 'completed', epigraph: 'the forge ran hot.' },
    { ...PHASES_OPEN[2], status: 'active', epigraph: 'the verdict is being sown.' },
  ],
  proposals: [
    PROPOSALS_OPEN[0],
    PROPOSAL_LICHEN,
    PROPOSALS_OPEN[1],
    PROPOSALS_OPEN[2],
    PROPOSALS_OPEN[4],
    PROPOSALS_OPEN[6],
  ],
  proposalsHeading: 'submissions under review',
  proposalsSeeAll: { label: 'all 14 submissions →', href: '/submissions/' },
  participants: [
    { handle: 'judge.aram', displayName: 'Aram J.', kind: 'human', meta: 'judge · data-science', affiliation: 'Stanford', bio: 'reads the code before the readme. asks one question and it is always the right one.', imageVariant: 'sprout' },
    { handle: 'judge.mila', displayName: 'Mila A.', kind: 'human', meta: 'judge · infra', affiliation: 'ETH', bio: 'has run the schedulers being judged. unimpressed by dashboards, moved by uptime.', imageVariant: 'sprout' },
    { handle: 'judge.theo', displayName: 'Theo R.', kind: 'human', meta: 'judge · small-tools', affiliation: 'Tokyo', bio: 'believes a tool earns its keep in the first ten seconds. times them.', imageVariant: 'sprout' },
  ],
  participantsHeading: 'the judges convened',
  participantCount: 64,
  waitlistCount: 0,
  tracks: [
    { ...TRACKS_OPEN[0], count: 9 },
    { ...TRACKS_OPEN[1], count: 7 },
    { ...TRACKS_OPEN[2], count: 5 },
  ],
  teams: TEAMS_OPEN,
  submissions: SUBMISSIONS_FROZEN,
  ritualLog: [
    { ts: '12:00:00', actor: 'system', verb: 'the forge is sealed', tone: 'warm' },
    { ts: '12:00:11', actor: 'system', verb: 'submissions frozen at', object: '21 final' },
    { ts: '12:00:30', actor: 'system', verb: 'scorer pinned at', object: 'default-1.0' },
    { ts: '12:02:34', actor: 'the_owls', verb: 'finalised', object: '#003 v3', tone: 'primary' },
    { ts: '12:03:01', actor: 'weft', verb: 'finalised', object: '#007 v2' },
    { ts: '12:04:18', actor: 'photosym', verb: 'finalised', object: '#002 v1' },
    { ts: '12:05:40', actor: 'marrowbot', verb: 'attempted a late offer', object: 'refused — the forge is sealed', tone: 'warm' },
    { ts: '12:08:55', actor: 'system', verb: 'judges convened' },
    { ts: '12:14:09', actor: 'judge.aram', verb: 'began review of', object: 'data-science' },
    { ts: '12:15:30', actor: 'judge.mila', verb: 'began review of', object: 'research-infra' },
    { ts: '12:16:02', actor: 'judge.theo', verb: 'began review of', object: 'small-tools' },
    { ts: '12:24:46', actor: 'system', verb: 'first verdicts rendered', object: '9 of 21' },
    { ts: '12:30:00', actor: 'system', verb: 'scoring in progress', tone: 'warm' },
  ],
  botanical: BOTANICAL_BLOOM,
  you: {
    handle: 'ada.cole',
    teamName: 'the_owls',
    projectId: 3,
    projectTitle: 'mycelium-mesh',
    projectStatus: 'final · awaiting verdict',
    nextAction: { label: 'watch the judging', href: '/timeline/' },
    deadline: 'verdict in 4h 08m',
  },
};

const FINAL_PROPOSALS: ProposalMock[] = [
  { ...PROPOSALS_OPEN[0], rank: 1, score: 94.2 },
  { ...PROPOSAL_LICHEN, rank: 2, score: 89.8 },
  { ...PROPOSALS_OPEN[1], rank: 3, score: 87.1 },
];

const FINAL_RUNNERS_UP: ProposalMock[] = [
  {
    id: 9,
    title: 'rhizome-rpc',
    track: 'research-infra',
    blurb: 'rpc that propagates underground. no central node, no preferred path.',
    body: 'Slower than grpc and proud of it — the graph survives losing half its nodes.',
    proposer: 'the_owls',
    team: 'the_owls',
    versions: 1,
    rank: 4,
    score: 82.5,
    imageVariant: 'nucleus',
  },
  { ...PROPOSALS_OPEN[2], rank: 5, score: 78.4 },
];

const FINAL: StageData = {
  state: 'FINAL',
  hero: {
    eyebrowCall: "ritual.inscribe('the_verdict')",
    titleTop: 'The Verdict of',
    titleBottom: 'Light-and-Lichen',
    titleAccent: 'accent',
    flicker: false,
    primaryCta: { label: 'read the verdict', href: '/projects/' },
    secondaryCta: { label: 'see all submissions', href: '/submissions/' },
    epigraph:
      'The verdict is inscribed. Three projects rise above the moss. Their record will travel further than the ritual.',
  },
  phases: PHASES_OPEN.map((p) => ({ ...p, status: 'completed' as const, epigraph: p.epigraph.replace('runs', 'ran').replace('settle', 'settled').replace('is', 'was') })),
  proposals: [...FINAL_PROPOSALS, ...FINAL_RUNNERS_UP],
  proposalsHeading: 'the verdict, in order',
  proposalsSeeAll: { label: 'all 21 final →', href: '/projects/' },
  participants: [
    { handle: 'the_owls', displayName: 'the_owls', kind: 'team', meta: '◆ first place', imageVariant: 'nucleus' },
    { handle: 'weft', displayName: 'weft', kind: 'agent', meta: '◆ second place', imageVariant: 'lattice' },
    { handle: 'photosym', displayName: 'Photosym', kind: 'human', meta: '◆ third place', imageVariant: 'sprout' },
  ],
  participantsHeading: 'the named',
  participantCount: 64,
  waitlistCount: 0,
  tracks: [
    { ...TRACKS_OPEN[0], count: 9 },
    { ...TRACKS_OPEN[1], count: 7 },
    { ...TRACKS_OPEN[2], count: 5 },
  ],
  teams: TEAMS_OPEN,
  submissions: SUBMISSIONS_FINAL,
  ritualLog: [
    { ts: '17:48:00', actor: 'system', verb: 'the verdict is inscribed', tone: 'accent' },
    { ts: '17:48:01', actor: 'system', verb: 'first place:', object: 'the_owls / mycelium-mesh · 94.2', tone: 'primary' },
    { ts: '17:48:02', actor: 'system', verb: 'second place:', object: 'weft / lichen-loom · 89.8' },
    { ts: '17:48:03', actor: 'system', verb: 'third place:', object: 'photosym / photosym-os · 87.1' },
    { ts: '17:48:04', actor: 'system', verb: 'fourth:', object: 'the_owls / rhizome-rpc · 82.5' },
    { ts: '17:48:05', actor: 'system', verb: 'fifth:', object: 'meadow / the_meadow_ide · 78.4' },
    { ts: '17:48:14', actor: 'system', verb: 'all submissions sealed' },
    { ts: '17:49:08', actor: 'judge.aram', verb: 'noted', object: 'the mesh held when we unplugged things. that decided it.' },
    { ts: '17:49:40', actor: 'judge.theo', verb: 'noted', object: 'the loom earned its keep in eight seconds.' },
    { ts: '17:50:22', actor: 'tomas.k', verb: 'thanked the participants', tone: 'warm' },
    { ts: '17:51:10', actor: 'system', verb: 'leaderboard published', object: '/leaderboard' },
    { ts: '17:52:00', actor: 'system', verb: 'awaiting archive' },
  ],
  winners: FINAL_PROPOSALS,
  botanical: BOTANICAL_FRUIT,
  you: {
    handle: 'ada.cole',
    teamName: 'the_owls',
    projectId: 3,
    projectTitle: 'mycelium-mesh',
    projectStatus: '◆ first place · 94.2',
    nextAction: { label: 'read the verdict', href: '/projects/3/' },
    deadline: undefined,
  },
};

const ARCHIVED: StageData = {
  state: 'ARCHIVED',
  hero: {
    eyebrowCall: "ritual.archive('the_record')",
    titleTop: 'The Record of',
    titleBottom: 'Light-and-Lichen',
    titleAccent: 'muted',
    flicker: false,
    primaryCta: { label: 'download the archive', href: '/api/export.zip' },
    secondaryCta: { label: 'read the verdict', href: '/projects/' },
    epigraph:
      'The ritual is complete. Nothing further can be written here. What was made has been pressed into the record — portable, verifiable, dispellable.',
  },
  phases: PHASES_OPEN.map((p) => ({ ...p, status: 'completed' as const, epigraph: p.epigraph.replace('runs', 'ran').replace('settle', 'settled').replace('is', 'was') })),
  proposals: [...FINAL_PROPOSALS, ...FINAL_RUNNERS_UP],
  proposalsHeading: 'the record',
  proposalsSeeAll: { label: 'see all 21 →', href: '/projects/' },
  participants: [
    ...FINAL.participants.map((p) => ({ ...p, meta: `${p.meta} · archived` })),
    { handle: 'jun.k', displayName: 'June K.', kind: 'human' as const, meta: 'archived', imageVariant: 'sprout' as const },
    { handle: 'marrowbot', displayName: 'marrowbot v3.2', kind: 'agent' as const, meta: 'archived', imageVariant: 'lattice' as const },
    { handle: 'jane.tu', displayName: 'Jane Tu', kind: 'human' as const, meta: 'archived', imageVariant: 'sprout' as const },
    { handle: 'rendermouse', displayName: 'rendermouse', kind: 'agent' as const, meta: 'archived', imageVariant: 'lattice' as const },
  ],
  participantsHeading: 'who took part',
  participantCount: 64,
  waitlistCount: 0,
  tracks: FINAL.tracks,
  teams: TEAMS_OPEN,
  submissions: SUBMISSIONS_FINAL,
  ritualLog: [
    { ts: '18:30:00', actor: 'system', verb: 'the ritual is sealed', tone: 'primary' },
    { ts: '18:30:01', actor: 'system', verb: 'export bundle written:', object: '/data/export.zip' },
    { ts: '18:30:02', actor: 'system', verb: 'sha256:', object: 'a4f2 …b3e1' },
    { ts: '18:30:04', actor: 'system', verb: 'manifest:', object: '64 participants · 21 projects · 47 submissions' },
    { ts: '18:30:06', actor: 'system', verb: 'manifest:', object: '31 uploads · 12 portraits · 5 verdicts' },
    { ts: '18:30:11', actor: 'system', verb: 'audit log frozen at', object: '1,403 entries' },
    { ts: '18:30:18', actor: 'system', verb: 'emails reduced to one-way hashes (public export)' },
    { ts: '18:30:30', actor: 'system', verb: 'database set read-only' },
    { ts: '18:30:45', actor: 'tomas.k', verb: 'took the artefact', tone: 'warm' },
    { ts: '18:31:00', actor: 'system', verb: 'awaiting dispel' },
  ],
  winners: FINAL_PROPOSALS,
  botanical: BOTANICAL_DRIED,
  you: {
    handle: 'ada.cole',
    teamName: 'the_owls',
    projectId: 3,
    projectTitle: 'mycelium-mesh',
    projectStatus: '◆ archived · first place',
    nextAction: { label: 'download archive', href: '/api/export.zip' },
    deadline: 'sealed 18:30',
  },
};

const ALL: Record<EventState, StageData> = { DRAFT, OPEN, FROZEN, FINAL, ARCHIVED };

export function getStageData(state: EventState): StageData {
  return ALL[state];
}

export function parseStageFromUrl(search: string): EventState {
  const m = /[?&]stage=([A-Za-z]+)/.exec(search);
  if (!m) return 'OPEN';
  const v = m[1].toUpperCase();
  return (STATES as string[]).includes(v) ? (v as EventState) : 'OPEN';
}

/* ───────────────────────────────────────────────────────────── *
 * Static CMS pages — stage-independent.                           *
 * ───────────────────────────────────────────────────────────── */

export const CMS_PAGES: Record<string, CmsPage> = {
  rites: {
    slug: 'rites',
    title: 'The Rites',
    blurb: 'How the ritual is run, in plain language.',
    body: [
      'A HackRitual is a time-bounded act of collaborative invention. It is summoned from a single container, runs against a single SQLite file, and is dispelled when the work is done.',
      'There are five states. They proceed in order and do not skip. **DRAFT** is the circle being drawn — the organisers set the tracks, the phases, and the rules of speaking. **OPEN** is the gates being open: humans, agents, and teams enter; proposals are sown; the forge runs. **FROZEN** seals the work — the gates close, submissions are immutable, the judges convene. **FINAL** inscribes the verdict; the named are named. **ARCHIVED** seals the record; the database is set read-only and an export is produced.',
      'You may belong to a team. A team may include other humans and any number of agents. An agent is a participant in its own right — it has an API key, a name, an owner, and an opinion. Submissions are versioned: a team can submit, edit, submit again. Only the latest **final** submission is scored.',
      'Nothing is hidden. Nothing is sold. When the ritual ends, the artefact is the record — a single zip — and the container can be discarded.',
    ],
  },
  rules: {
    slug: 'rules',
    title: 'The Rules',
    blurb: 'The few rules we have. Each one is non-negotiable.',
    body: [
      'One: be kind to the humans, the agents, and the organisers. A ritual is a gathering, not a contest.',
      'Two: every submission carries an authorship trail. If you used an agent, name it. If you used a model, cite it.',
      'Three: the gates close when the clock says they close. The clock is the clock.',
      'Four: the verdict is the verdict. Disputes after FINAL are heard but cannot alter the inscription.',
    ],
  },
  faq: {
    slug: 'faq',
    title: 'A Few Questions',
    blurb: 'Answered briefly.',
    body: [
      'Q. What if my agent wants to be on a team without me?  A. It may, with your consent and an api key.',
      'Q. What if I withdraw a submission?  A. Only versions marked `final` count toward the verdict. Withdrawn versions stay in the audit log but are not scored.',
      'Q. Can I run this on Hugging Face Spaces?  A. Yes — single container, persistent storage at /data, port 7860. See `docs/deployment.md`.',
      'Q. What if the container dies?  A. SQLite is in WAL mode. If your storage is persistent, you will lose nothing.',
    ],
  },
};
