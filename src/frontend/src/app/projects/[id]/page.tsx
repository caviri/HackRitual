import { ProjectDetail } from './project-detail';

export function generateStaticParams() {
  // Pre-render the IDs that exist across our mock datasets.
  return [{ id: '1' }, { id: '2' }, { id: '3' }, { id: '7' }];
}

export default function ProjectDetailPage() {
  return <ProjectDetail />;
}
