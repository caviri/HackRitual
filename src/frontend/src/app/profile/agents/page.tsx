'use client';

import { PageHeader } from '../../../components/page-header';
import { AgentsPanel } from '../../../components/agents-panel';

export default function ProfileAgentsPage() {
  return (
    <>
      <PageHeader
        prompt="ritual.me.agents()"
        title="Your agents"
        subtitle="Mint API keys for bots and processes you own. They participate in your name."
        back="/profile/"
        backLabel="your portrait"
      />
      <section className="mx-auto w-full max-w-4xl px-6 py-10">
        <AgentsPanel scope="self" />
      </section>
    </>
  );
}
