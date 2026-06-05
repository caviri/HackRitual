# 10 — Frontend Foundation

**Milestone:** MVP-1
**Priority:** High
**Dependencies:** [01-project-setup-docker](01-project-setup-docker.md), [03-authentication](03-authentication.md)
**Specs reference:** §10 (User Flows)

---

## Overview

Build the Next.js frontend application that serves the participant-facing experience: login, event dashboard, participant registration, submission creation, leaderboard, and results. The frontend is built as a static export served by FastAPI from the same container.

---

## Tasks

### 10.1 Next.js Project Setup

- Initialize Next.js 14+ with App Router
- Configure for static export (`output: 'export'` in next.config.js)
- Set up:
  - TypeScript
  - Tailwind CSS for styling
  - Path aliases (`@/components`, `@/lib`, etc.)
  - Environment variables: `NEXT_PUBLIC_API_URL` (for dev proxy)

**Directory structure:**
```
frontend/src/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Landing / event info
│   ├── login/page.tsx          # Login flow
│   ├── dashboard/page.tsx      # Participant dashboard
│   ├── submissions/
│   │   ├── page.tsx            # My submissions list
│   │   └── new/page.tsx        # Create submission
│   ├── leaderboard/page.tsx    # Public leaderboard
│   ├── profile/page.tsx        # Participant profile
│   ├── teams/
│   │   ├── page.tsx            # Team management
│   │   └── join/page.tsx       # Join team
│   ├── results/page.tsx        # Final results (post-event)
│   ├── privacy/page.tsx        # Privacy notice
│   └── (admin)/                # Admin routes (task 09)
├── components/
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Footer.tsx
│   │   └── Sidebar.tsx
│   ├── auth/
│   │   ├── LoginForm.tsx
│   │   ├── CodeVerification.tsx
│   │   └── AuthGuard.tsx
│   ├── event/
│   │   ├── EventBanner.tsx
│   │   ├── EventStatus.tsx
│   │   └── EventTimeline.tsx
│   ├── submissions/
│   │   ├── SubmissionForm.tsx
│   │   ├── SubmissionCard.tsx
│   │   └── SubmissionList.tsx
│   ├── leaderboard/
│   │   ├── LeaderboardTable.tsx
│   │   └── RankBadge.tsx
│   └── ui/                     # Shared UI primitives
│       ├── Button.tsx
│       ├── Input.tsx
│       ├── Modal.tsx
│       ├── Badge.tsx
│       └── Card.tsx
├── lib/
│   ├── api.ts                  # API client (fetch wrapper)
│   ├── auth.ts                 # Auth helpers (cookie check, redirect)
│   └── types.ts                # TypeScript types matching API schemas
└── styles/
    └── globals.css
```

### 10.2 API Client

Create a typed API client:

```typescript
// frontend/src/lib/api.ts

const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api';

class ApiClient {
  private async request<T>(path: string, options?: RequestInit): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
      credentials: 'include',  // send cookies
      headers: { 'Content-Type': 'application/json', ...options?.headers },
      ...options,
    });
    if (!res.ok) {
      const error = await res.json().catch(() => ({}));
      throw new ApiError(res.status, error);
    }
    return res.json();
  }

  // Auth
  requestCode(email: string) { ... }
  verifyCode(email: string, code: string) { ... }
  logout() { ... }
  getMe() { ... }

  // Event
  getEvent() { ... }

  // Participants
  createParticipant(data: CreateParticipantInput) { ... }
  getMyParticipant() { ... }
  createTeam(data: CreateTeamInput) { ... }
  joinTeam(inviteCode: string) { ... }

  // Submissions
  createSubmission(data: FormData) { ... }
  getMySubmissions() { ... }
  getSubmission(id: string) { ... }

  // Leaderboard
  getLeaderboard(params?: LeaderboardParams) { ... }
}

export const api = new ApiClient();
```

### 10.3 Authentication Flow UI

**Login page (`/login`):**

1. **Email step:** Input field + "Send Code" button
2. **Code step:** 6-digit input + "Verify" button + "Resend" link
3. **Success:** Redirect to `/dashboard`

Component: `LoginForm.tsx` + `CodeVerification.tsx`

- Show clear feedback: "Code sent to your email"
- Handle errors: "Too many attempts", "Invalid code", "Code expired"
- Auto-focus the code input after sending

**Auth Guard:** Wrap protected routes with `AuthGuard`:
```typescript
// Checks if user is authenticated, redirects to /login if not
// Reads auth state from /api/auth/me on mount
```

### 10.4 Landing Page

`/` — Event information page:

- Event title and tagline
- Event status badge
- Start/end dates with countdown (if upcoming)
- Description / rules
- Call-to-action: "Join" or "Login" button
- Leaderboard preview (top 5)
- Privacy notice footer link

### 10.5 Participant Dashboard

`/dashboard` — Main hub after login:

- Welcome message with participant name
- Event status and phase indicator
- Quick stats:
  - My submissions count
  - My best/latest score
  - My rank on leaderboard
- Action cards:
  - "New Submission" (if event is OPEN)
  - "View Leaderboard"
  - "My Submissions"
  - "Team" (if applicable)
- Event timeline showing current phase

### 10.6 Submission Pages

**Create Submission (`/submissions/new`):**

- Form with:
  - Title (text input)
  - Description (textarea)
  - Tags (multi-select or comma-separated)
  - File upload (drag-and-drop zone, multi-file)
  - JSON payload editor (optional, for advanced users)
- Client-side validation:
  - File size and type checks
  - Required fields
- Submit button with loading state
- Success → redirect to submission detail

**My Submissions (`/submissions`):**

- List of all submissions with:
  - Title, date, status badge
  - Score (if scored)
  - Actions: view, withdraw
- Sort by date or score

**Submission Detail (`/submissions/[id]`):**

- Full metadata display
- File previews (images inline, others as download links)
- Score breakdown (if scored)
- Status timeline (received → scored)

### 10.7 Leaderboard Page

`/leaderboard` — Public leaderboard:

- Table with: rank, participant name, type badge, score, submission count
- Highlight current user's row
- Track filter tabs (if tracks exist)
- Auto-refresh every 30 seconds during OPEN state
- Show "Final Results" banner when state is FINAL

### 10.8 Profile & Team Pages

**Profile (`/profile`):**
- Display name, affiliation, links
- Edit form
- Team info (if member)

**Teams (`/teams`):**
- Current team details
- Member list
- Invite code display (captain only) with copy button
- Join team form (input invite code)

### 10.9 Results Page

`/results` — Available when event is FINAL or ARCHIVED:

- Final leaderboard (frozen)
- Winner highlights
- Archive download link (if available)
- Event summary stats

### 10.10 Privacy Notice Page

`/privacy` — Static page:

- Clear statement about cookies (session only)
- Data collection description
- No tracking notice
- Per specs §14.10

### 10.11 Responsive Design & Theming

- Mobile-first responsive design
- Event-themed colors (configurable via CSS variables)
- Dark mode support (follows system preference)
- Accessible: proper labels, focus management, color contrast

---

## Acceptance Criteria

- [ ] Next.js app builds as static export and is served by FastAPI
- [ ] Login flow (email → code → session) works end-to-end
- [ ] Protected routes redirect to login when unauthenticated
- [ ] Dashboard shows relevant info and actions based on event state
- [ ] Submission form handles file uploads and metadata
- [ ] Leaderboard displays ranked participants with real-time updates
- [ ] Team creation and join via invite code works
- [ ] Privacy notice page present with accurate content
- [ ] UI is responsive on mobile, tablet, and desktop
- [ ] API client handles errors gracefully with user feedback

---

## Developer Notes

- Use Next.js static export mode — the app runs client-side only, no SSR needed
- During development, use `next.config.js` rewrites to proxy `/api` to the FastAPI dev server
- Consider shadcn/ui as a component library (built on Tailwind + Radix)
- Use React Context for auth state (current user, participant)
- Avoid heavy dependencies — keep the bundle small for Spaces hosting
- Test with slow network conditions (Spaces can have limited bandwidth)
- The frontend must work with cookies (credentials: 'include' on all API calls)
