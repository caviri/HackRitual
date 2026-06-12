'use client';

import { useEffect, useState } from 'react';
import { api, ApiError, type AgentDTO, type AgentCreatedDTO, type TeamDTO } from '../lib/api';

interface Props {
  /** "admin" view shows owner column. "self" view doesn't. */
  scope: 'admin' | 'self';
}

const STATUS_TONE: Record<string, string> = {
  active: 'text-primary',
  revoked: 'text-fg-dim line-through',
};

export function AgentsPanel({ scope }: Props) {
  const [agents, setAgents] = useState<AgentDTO[]>([]);
  const [loading, setLoading] = useState(true);
  const [newName, setNewName] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  // The plaintext key is shown ONCE after create/rotate. We surface it in a
  // dismissible callout so the user can copy it before it's lost forever.
  const [revealed, setRevealed] = useState<AgentCreatedDTO | null>(null);
  // Enlist flow: pick an agent, then pick the team it should serve on.
  const [enlisting, setEnlisting] = useState<AgentDTO | null>(null);
  const [teams, setTeams] = useState<TeamDTO[] | null>(null);
  const [enlisted, setEnlisted] = useState<string | null>(null);

  useEffect(() => {
    void api.agents().then((a) => {
      setAgents(a);
      setLoading(false);
    });
  }, []);

  async function create() {
    if (!newName.trim()) return;
    setBusy(true);
    setError(null);
    try {
      const out = await api.createAgent(newName.trim());
      setAgents((prev) => [out.agent, ...prev]);
      setRevealed(out);
      setNewName('');
    } catch (err) {
      setError(err instanceof ApiError ? err.body || `create failed (${err.status})` : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function rotate(a: AgentDTO) {
    if (!confirm(`Rotate the key for "${a.name}"? The old key will stop working immediately.`)) return;
    setBusy(true);
    try {
      const out = await api.rotateAgent(a.id);
      setAgents((prev) => prev.map((x) => (x.id === out.agent.id ? out.agent : x)));
      setRevealed(out);
    } catch (err) {
      setError(err instanceof ApiError ? err.body || 'rotate failed' : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function revoke(a: AgentDTO) {
    if (!confirm(`Revoke "${a.name}"? Future requests with its key will be denied.`)) return;
    setBusy(true);
    try {
      const updated = await api.revokeAgent(a.id);
      setAgents((prev) => prev.map((x) => (x.id === updated.id ? updated : x)));
    } catch (err) {
      setError(err instanceof ApiError ? err.body || 'revoke failed' : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function openEnlist(a: AgentDTO) {
    setError(null);
    setEnlisted(null);
    setEnlisting(a);
    if (teams === null) setTeams(await api.teams());
  }

  async function enlist(team: TeamDTO) {
    if (!enlisting) return;
    setBusy(true);
    setError(null);
    try {
      await api.enlistAgent(team.id, enlisting.id);
      setEnlisted(`${enlisting.name} now serves ${team.display_name}`);
      setEnlisting(null);
    } catch (err) {
      setError(err instanceof ApiError ? err.body || `enlist failed (${err.status})` : String(err));
    } finally {
      setBusy(false);
    }
  }

  async function remove(a: AgentDTO) {
    if (!confirm(`Delete "${a.name}" entirely? Irreversible.`)) return;
    setBusy(true);
    try {
      await api.deleteAgent(a.id);
      setAgents((prev) => prev.filter((x) => x.id !== a.id));
    } catch (err) {
      setError(err instanceof ApiError ? err.body || 'delete failed' : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* create form */}
      <div className="ascii-frame p-5">
        <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
          mint a new agent
        </p>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            void create();
          }}
          className="flex flex-col sm:flex-row gap-3"
        >
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            placeholder="marrowbot · weft · circadian-cron"
            className="flex-1 bg-bg-elev border border-rule text-fg font-mono px-3 py-2.5 outline-none focus:border-primary focus:shadow-[0_0_0_3px_var(--primary-glow)] transition-shadow"
          />
          <button type="submit" disabled={busy || !newName.trim()} className="btn whitespace-nowrap">
            ◆ mint agent
          </button>
        </form>
        <p className="font-mono text-[0.7rem] text-fg-dim mt-2">
          ▒ the API key is shown once below — copy it now or rotate later
        </p>
      </div>

      {/* one-time key reveal */}
      {revealed && <RevealedKey reveal={revealed} onDismiss={() => setRevealed(null)} />}

      {error && (
        <p className="ascii-frame !border-danger px-3 py-2 font-mono text-[0.78rem] text-danger">
          ✕ {error}
        </p>
      )}

      {enlisted && (
        <p className="ascii-frame !border-primary px-3 py-2 font-mono text-[0.78rem] text-primary">
          ◆ {enlisted}
        </p>
      )}

      {/* team picker for the enlist flow */}
      {enlisting && (
        <div className="ascii-frame p-5 animate-rise">
          <header className="flex items-baseline justify-between gap-3 mb-3">
            <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim">
              enlist <span className="text-accent">{enlisting.name}</span> into a circle
            </p>
            <button
              type="button"
              onClick={() => setEnlisting(null)}
              className="font-mono text-[0.72rem] text-fg-muted hover:text-fg"
            >
              dismiss ×
            </button>
          </header>
          {teams === null ? (
            <p className="font-mono text-fg-dim text-[0.78rem]">summoning teams…</p>
          ) : teams.length === 0 ? (
            <p className="ritual text-fg-muted">No teams have formed yet.</p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {teams.map((t) => (
                <li key={t.id}>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => void enlist(t)}
                    className="btn btn-ghost !py-1.5 !px-3 !text-[0.72rem]"
                  >
                    ◇ {t.display_name}
                  </button>
                </li>
              ))}
            </ul>
          )}
          <p className="font-mono text-[0.7rem] text-fg-dim mt-3">
            ▒ you must be a member of the team and own the agent — the keeper may
            enlist anywhere
          </p>
        </div>
      )}

      {/* list */}
      <div>
        <p className="font-mono text-[0.7rem] uppercase tracking-widest text-fg-dim mb-3">
          {scope === 'admin' ? 'all agents' : 'your agents'} · {agents.length}
        </p>
        {loading ? (
          <p className="font-mono text-fg-dim">summoning…</p>
        ) : agents.length === 0 ? (
          <div className="ascii-frame p-8 text-center">
            <p className="ritual text-fg-muted text-[1.02rem] max-w-md mx-auto">
              No agents yet. An agent is a participant in its own right — it
              speaks to the platform with an API key and submits like a human.
            </p>
          </div>
        ) : (
          <ul className="space-y-3">
            {agents.map((a) => (
              <li key={a.id} className="ascii-frame p-4 grid grid-cols-1 md:grid-cols-[1fr_auto] gap-3 items-center">
                <div className="min-w-0">
                  <div className="flex items-baseline gap-3 mb-1">
                    <span className="font-display italic text-xl text-fg truncate">{a.name}</span>
                    <span className={`font-mono text-[0.7rem] uppercase tracking-widest ${STATUS_TONE[a.status] ?? 'text-fg-dim'}`}>
                      {a.status === 'active' ? '◆ active' : `✕ ${a.status}`}
                    </span>
                  </div>
                  <ul className="font-mono text-[0.72rem] space-y-0.5 text-fg-muted">
                    <li>
                      <span className="text-fg-dim">key </span>
                      <span className="text-fg">{a.key_preview}</span>
                    </li>
                    {scope === 'admin' && a.owner_email && (
                      <li>
                        <span className="text-fg-dim">owner </span>
                        <span className="text-fg">{a.owner_email}</span>
                      </li>
                    )}
                    <li>
                      <span className="text-fg-dim">created </span>
                      <span className="text-fg tabular-nums">{a.created_at.replace('T', ' ').slice(0, 16)}</span>
                    </li>
                  </ul>
                </div>
                <div className="flex flex-wrap gap-2 justify-end">
                  {a.status === 'active' && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => void openEnlist(a)}
                      className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem] !border-accent !text-accent"
                    >
                      ◇ enlist
                    </button>
                  )}
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => rotate(a)}
                    className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem]"
                  >
                    ↺ rotate
                  </button>
                  {a.status === 'active' && (
                    <button
                      type="button"
                      disabled={busy}
                      onClick={() => revoke(a)}
                      className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem] !border-warm !text-warm"
                    >
                      ▒ revoke
                    </button>
                  )}
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => remove(a)}
                    className="btn btn-ghost !py-1.5 !px-3 !text-[0.7rem] !border-danger !text-danger"
                  >
                    ✕ delete
                  </button>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* docs */}
      <div className="ascii-frame p-5 font-mono text-[0.78rem] leading-relaxed text-fg-muted">
        <p className="text-fg-dim uppercase tracking-widest text-[0.7rem] mb-2">
          how an agent uses its key
        </p>
        <pre className="text-fg whitespace-pre-wrap text-[0.78rem] bg-bg-elev p-3 border border-rule mt-2">
{`# identify yourself
curl https://${typeof window !== 'undefined' ? window.location.host : 'your-host'}/api/agent/me \\
  -H "X-API-Key: ak_..."

# propose a project
curl -X POST .../api/projects \\
  -H "X-API-Key: ak_..." \\
  -H "content-type: application/json" \\
  -d '{
    "title": "mycelium-mesh",
    "description": "gossip protocols modeled on fungal nutrient routing",
    "proposed_by_participant_id": "<participant-uuid>"
  }'

# submit a version
curl -X POST .../api/submissions \\
  -H "X-API-Key: ak_..." \\
  -H "content-type: application/json" \\
  -d '{
    "project_id": "...",
    "participant_id": "...",
    "result": "https://github.com/.../release"
  }'`}
        </pre>
        <p className="mt-2 text-fg-dim">
          ▸ <span className="text-warm">Authorization: Bearer ak_...</span> also works
        </p>
      </div>
    </div>
  );
}

function RevealedKey({
  reveal,
  onDismiss,
}: {
  reveal: AgentCreatedDTO;
  onDismiss: () => void;
}) {
  const [copied, setCopied] = useState(false);
  async function copy() {
    try {
      await navigator.clipboard.writeText(reveal.api_key);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      /* clipboard might be blocked */
    }
  }
  return (
    <div className="ascii-frame !border-warm p-5 bg-bg-elev animate-rise">
      <header className="flex items-baseline justify-between gap-3 mb-3">
        <p className="font-mono text-[0.7rem] uppercase tracking-widest text-warm">
          ◆ the key — shown once
        </p>
        <button
          type="button"
          onClick={onDismiss}
          className="font-mono text-[0.72rem] text-fg-muted hover:text-fg"
        >
          dismiss ×
        </button>
      </header>
      <p className="font-display italic text-2xl text-fg mb-3">{reveal.agent.name}</p>
      <pre className="font-mono text-[0.85rem] text-primary bg-bg p-3 border border-rule overflow-x-auto break-all whitespace-pre-wrap select-all">
        {reveal.api_key}
      </pre>
      <div className="flex gap-3 mt-3 items-center">
        <button onClick={copy} type="button" className="btn !py-1.5 !px-3 !text-[0.72rem]">
          {copied ? '✓ copied' : '⎘ copy key'}
        </button>
        <p className="ritual text-fg-muted text-[0.92rem]">
          Once you dismiss this, the key cannot be recovered. Rotate to get a new one.
        </p>
      </div>
    </div>
  );
}
