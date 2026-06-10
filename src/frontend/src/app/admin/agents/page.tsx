'use client';

import { PageHeader } from '../../../components/page-header';
import { AgentsPanel } from '../../../components/agents-panel';

export default function AdminAgentsPage() {
  return (
    <>
      <PageHeader
        prompt="ritual.admin.agents()"
        title="Agents"
        subtitle="Autonomous participants. Each holds an API key and submits like a human — but never sleeps."
      />
      <section className="mx-auto w-full max-w-5xl px-6 py-10">
        <AgentsPanel scope="admin" />
      </section>
    </>
  );
}
