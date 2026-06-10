import { CmsView } from './cms-view';

export function generateStaticParams() {
  return [{ slug: 'rites' }, { slug: 'rules' }, { slug: 'faq' }];
}

export default function CmsPage() {
  return <CmsView />;
}
