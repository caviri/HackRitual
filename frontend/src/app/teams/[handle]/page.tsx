import { TeamDetail } from './team-detail';

export function generateStaticParams() {
  return [
    { handle: 'the_owls' },
    { handle: 'photosym' },
    { handle: 'meadow_solo' },
  ];
}

export default function TeamPage() {
  return <TeamDetail />;
}
