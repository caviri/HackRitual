import { TrackDetail } from './track-detail';

export function generateStaticParams() {
  return [
    { name: 'data-science' },
    { name: 'research-infra' },
    { name: 'small-tools' },
  ];
}

export default function TrackPage() {
  return <TrackDetail />;
}
