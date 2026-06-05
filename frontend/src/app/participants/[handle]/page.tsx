import { ParticipantDetail } from './participant-detail';

export function generateStaticParams() {
  // Pre-render the handles that appear across our datasets.
  return [
    { handle: 'ada.cole' },
    { handle: 'jun.k' },
    { handle: 'marrowbot' },
    { handle: 'the_owls' },
    { handle: 'weft' },
    { handle: 'photosym' },
    { handle: 'jane.tu' },
    { handle: 'rendermouse' },
    { handle: 'tomas.k' },
    { handle: 'judge.aram' },
    { handle: 'judge.mila' },
    { handle: 'judge.theo' },
  ];
}

export default function ParticipantPage() {
  return <ParticipantDetail />;
}
