'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { PageHeader } from '../../components/page-header';
import { useStage } from '../../lib/use-stage';
import {
  api,
  type ParticipantDTO,
  type ProjectDTO,
  type SubmissionDTO,
} from '../../lib/api';

const STATUS_GLYPH: Record<string, string> = {
  draft: '▒',
  final: '◆',
  withdrawn: '✕',
};

const STATUS_TONE: Record<string, string> = {
  draft: 'text-fg-muted',
  final: 'text-primary',
  withdrawn: 'text-fg-dim',
};

interface Row {
  key: string;
  versionLabel: string;
  projectTitle: string;
  projectHref: string;
  team: string;
  status: string;
  result?: string;
  modifiedAt: string;
  score?: number;
}

export default function SubmissionsPage() {
  const data = useStage();
  const [real, setReal] = useState<{
    subs: SubmissionDTO[];
    projects: ProjectDTO[];
    participants: ParticipantDTO[];
  } | null>(null);

  useEffect(() => {
    void Promise.all([
      api.submissions(),
      api.projects(),
      api.participants(),
    ]).then(([subs, projects, participants]) => {
      if (subs.length > 0) setReal({ subs, projects, participants });
    });
  }, []);

  const rows: (Row & { submissionHref?: string })[] = real
    ? real.subs.map((s) => {
        const project = real.projects.find((p) => p.id === s.project_id);
        const participant = real.participants.find(
          (p) => p.id === s.participant_id,
        );
        return {
          key: s.id,
          versionLabel: `v${s.version}`,
          projectTitle: project?.title ?? s.project_id.slice(0, 6),
          projectHref: `/project/?id=${s.project_id}`,
          submissionHref: `/submission/?id=${s.id}`,
          team: participant?.display_name ?? s.participant_id.slice(0, 6),
          status: s.status,
          result: s.result ?? undefined,
          modifiedAt: s.modified_at.slice(0, 16).replace('T', ' '),
        };
      })
    : data.submissions.map((s) => ({
        key: String(s.id),
        versionLabel: `v${s.version}`,
        projectTitle: s.projectTitle,
        projectHref: `/projects/${s.projectId}/`,
        team: s.team,
        status: s.status,
        result: s.result ?? undefined,
        modifiedAt: s.modifiedAt,
        score: s.score,
      }));

  const subtitle = {
    DRAFT: 'No submissions yet. They appear once the forge opens.',
    OPEN: "Every version of every team's work. One row per (project, team, version).",
    FROZEN: 'Sealed. Each final version is what the judges will see.',
    FINAL: 'The submissions that were scored, with their final marks.',
    ARCHIVED: 'The submissions of record. Preserved verbatim in the export bundle.',
  }[data.state];

  return (
    <>
      <PageHeader
        prompt="ritual.submissions()"
        title="Submissions"
        subtitle={subtitle}
        chip={real ? `${rows.length} live` : `${rows.length} versions`}
      />

      <section className="mx-auto w-full max-w-6xl px-6 py-10">
        <div className="flex justify-end mb-6">
          <Link href="/submissions/new/" className="btn">
            ◆ offer a submission
          </Link>
        </div>
        {rows.length === 0 ? (
          <div className="ascii-frame p-10 text-center">
            <p className="font-mono text-[0.78rem] text-fg-dim uppercase tracking-widest mb-3">
              $ submissions.list() → []
            </p>
            <p className="ritual text-fg-muted text-[1.05rem] max-w-md mx-auto">
              No versions yet. Submissions arrive as soon as the forge runs.
            </p>
          </div>
        ) : (
          <div className="ascii-frame overflow-x-auto">
            <table className="w-full font-mono text-[0.82rem]">
              <thead className="border-b border-rule bg-bg-elev">
                <tr className="text-[0.66rem] uppercase tracking-widest text-fg-dim">
                  <th className="text-left p-3 font-normal">ver</th>
                  <th className="text-left p-3 font-normal">project</th>
                  <th className="text-left p-3 font-normal">team</th>
                  <th className="text-left p-3 font-normal">status</th>
                  <th className="text-left p-3 font-normal">result</th>
                  <th className="text-right p-3 font-normal">modified</th>
                  <th className="text-right p-3 font-normal">score</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((s) => (
                  <tr
                    key={s.key}
                    className="border-t border-rule hover:bg-bg-elev/60 transition-colors"
                  >
                    <td className="p-3 text-fg tabular-nums">
                      {s.submissionHref ? (
                        <Link href={s.submissionHref} className="text-fg hover:text-primary">
                          {s.versionLabel}
                        </Link>
                      ) : (
                        s.versionLabel
                      )}
                    </td>
                    <td className="p-3">
                      <Link
                        href={s.projectHref}
                        className="text-fg hover:text-primary"
                      >
                        {s.projectTitle}
                      </Link>
                    </td>
                    <td className="p-3 text-fg-muted">{s.team}</td>
                    <td className={`p-3 ${STATUS_TONE[s.status]}`}>
                      <span className="mr-1.5" aria-hidden>
                        {STATUS_GLYPH[s.status]}
                      </span>
                      <span className="uppercase tracking-wider text-[0.72rem]">
                        {s.status}
                      </span>
                    </td>
                    <td className="p-3 text-fg-muted text-[0.75rem] truncate max-w-[24ch]">
                      {s.result ?? <span className="text-fg-dim">—</span>}
                    </td>
                    <td className="p-3 text-right text-fg-dim tabular-nums">
                      {s.modifiedAt}
                    </td>
                    <td className="p-3 text-right tabular-nums">
                      {s.score != null ? (
                        <span className="text-accent">{s.score.toFixed(1)}</span>
                      ) : (
                        <span className="text-fg-dim">—</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  );
}
