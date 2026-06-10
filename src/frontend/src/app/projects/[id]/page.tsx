import { ProjectDetail } from './project-detail';
import { STATES, getStageData } from '../../../lib/mocks';

export function generateStaticParams() {
  // Pre-render every proposal id that appears in ANY stage dataset, so no
  // mock card can link to a page that does not exist in the static export.
  const ids = new Set<number>();
  for (const state of STATES) {
    const data = getStageData(state);
    for (const p of data.proposals) ids.add(p.id);
    for (const w of data.winners ?? []) ids.add(w.id);
  }
  return [...ids].map((id) => ({ id: String(id) }));
}

export default function ProjectDetailPage() {
  return <ProjectDetail />;
}
