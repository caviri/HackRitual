'use client';

import { useEffect, useState } from 'react';
import { RitualLog } from './ritual-log';
import { ThemeSwitcher } from './theme-switcher';
import { getStageData, parseStageFromUrl, type LogEntry, type EventState } from '../lib/mocks';
import { api, backendPresent, type LogEntryDTO } from '../lib/api';

const LOG_LABEL: Record<EventState, string> = {
  DRAFT: 'log · circle drawn',
  OPEN: 'log · the forge running',
  FROZEN: 'log · gates sealed',
  FINAL: 'log · verdict inscribed',
  ARCHIVED: 'log · record sealed',
};

// The audit trail speaks in dotted actions; the footer speaks liturgy.
const VERB_FOR: Record<string, { verb: string; tone?: LogEntry['tone'] }> = {
  'event.created': { verb: 'the circle is drawn', tone: 'primary' },
  'event.transition': { verb: 'the ritual advanced', tone: 'primary' },
  'event.config_updated': { verb: 'the rules were bound' },
  'event.meta_updated': { verb: 'the rite was renamed' },
  'page.published': { verb: 'a page was published' },
  'application.received': { verb: 'a petition arrived', tone: 'warm' },
  'application.approved': { verb: 'a petition was granted', tone: 'primary' },
  'application.rejected': { verb: 'a petition was declined', tone: 'warm' },
  'participant.reserved': { verb: 'a seat was reserved', tone: 'warm' },
  'participant.registered': { verb: 'stepped into the circle' },
  'team.formed': { verb: 'a team was formed', tone: 'primary' },
  'agent.created': { verb: 'an agent was minted', tone: 'accent' },
  'agent.key_rotated': { verb: 'an agent key was rotated' },
  'agent.revoked': { verb: 'an agent was revoked', tone: 'warm' },
  'project.proposed': { verb: 'proposed' },
  'project.approved': { verb: 'a proposal was approved', tone: 'primary' },
  'submission.offered': { verb: 'offered work' },
  'submission.finalised': { verb: 'sealed an offering', tone: 'primary' },
  'submission.withdrawn': { verb: 'withdrew an offering', tone: 'warm' },
  'score.rendered': { verb: 'a verdict was rendered', tone: 'accent' },
  'verdict.inscribed': { verb: 'the verdict was inscribed', tone: 'accent' },
  'leaderboard.published': { verb: 'the standing was published' },
  'export.sealed': { verb: 'the artefact was sealed', tone: 'primary' },
  'record.closed': { verb: 'the record closed', tone: 'primary' },
  'user.admin_seeded': { verb: 'the keeper was seeded' },
  'user.role_changed': { verb: 'a role was recast' },
  'user.password_regenerated': { verb: 'a key was reforged' },
  'announcement.created': { verb: 'a dispatch was published', tone: 'primary' },
  'announcement.updated': { verb: 'a dispatch was recast' },
  'announcement.deleted': { verb: 'a dispatch was withdrawn', tone: 'warm' },
  'demo.rebuilt': { verb: 'the small worlds were regrown', tone: 'accent' },
  'users.csv_imported': { verb: 'the roster was imported' },
};

function auditToLogEntry(e: LogEntryDTO): LogEntry {
  const mapped = VERB_FOR[e.action] ?? { verb: e.action.replace('.', ' · ') };
  return {
    ts: new Date(e.ts).toLocaleTimeString('en-GB', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }),
    actor: e.actor ?? 'system',
    verb: mapped.verb,
    object: e.summary ?? undefined,
    tone: mapped.tone,
  };
}

export function Footer() {
  const [entries, setEntries] = useState<LogEntry[]>(getStageData('OPEN').ritualLog);
  const [state, setState] = useState<EventState>('OPEN');

  useEffect(() => {
    const s = parseStageFromUrl(window.location.search);
    setState(s);
    setEntries(getStageData(s).ritualLog);

    void backendPresent().then(async (present) => {
      if (!present) return;
      const [page, event] = await Promise.all([
        api.logPage({ limit: 12 }),
        api.event(),
      ]);
      if (event?.state) setState(event.state as EventState);
      setEntries((page?.entries ?? []).map(auditToLogEntry));
    });
  }, []);

  return (
    <footer className="border-t border-rule mt-32">
      <div className="mx-auto w-full max-w-6xl px-6 py-10 grid gap-10 lg:grid-cols-[1.4fr_1fr]">
        <div className="ascii-frame p-5">
          <RitualLog entries={entries} label={LOG_LABEL[state]} />
        </div>

        <div className="flex flex-col justify-between gap-6">
          <div className="font-mono text-[0.78rem] space-y-2 text-fg-muted">
            <div className="flex gap-3">
              <span className="text-fg-dim">$ ritual.info()</span>
            </div>
            <ul className="space-y-1 pl-3">
              <li>
                <span className="text-fg-dim">version  </span>
                <span className="text-fg">0.1.0</span>
              </li>
              <li>
                <span className="text-fg-dim">state    </span>
                <span className="text-primary">{state}</span>
              </li>
              <li>
                <span className="text-fg-dim">storage  </span>
                <span className="text-fg">/data/app.db</span>
              </li>
              <li>
                <span className="text-fg-dim">api      </span>
                <a href="/api/health" className="text-accent hover:underline">
                  /api/health ↗
                </a>
              </li>
              <li>
                <span className="text-fg-dim">handbook </span>
                <a href="/docs/" className="text-primary hover:underline">
                  the process ↗
                </a>
              </li>
              <li>
                <span className="text-fg-dim">api docs </span>
                <a href="/api/docs" className="text-primary hover:underline">
                  the spellbook ↗
                </a>
              </li>
              <li>
                <span className="text-fg-dim">privacy  </span>
                <a href="/privacy/" className="text-primary hover:underline">
                  what we remember ↗
                </a>
              </li>
              <li>
                <span className="text-fg-dim">source   </span>
                <span className="text-fg">single container · one ritual</span>
              </li>
            </ul>
          </div>

          <div className="flex items-end justify-between gap-4 pt-4 border-t border-rule">
            <p className="ritual text-fg-muted text-[0.95rem] max-w-xs">
              Forged from nothing. Exported as record. Dispelled when done.
            </p>
            <ThemeSwitcher />
          </div>
        </div>
      </div>
    </footer>
  );
}
