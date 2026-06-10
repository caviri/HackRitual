import { WarningBand, AdminSubNav } from '../../components/admin-chrome';
import { AuthGuard } from '../../components/auth-guard';

/**
 * Wraps every /admin/* page in a hazard-banded container.
 *
 *   ▒▒▒▒▒▒  KEEPER'S CONSOLE · AUTHORIZED HOLDERS ONLY  ▒▒▒▒▒▒
 *   ── sub-nav (overview · proposals · agents · …) ────────────
 *
 *                       {child page content}
 *
 *   ▒▒▒▒▒▒  EACH ACTION IS INSCRIBED · MOVE WITH INTENTION  ▒▒▒▒▒▒
 *
 * The bands carry the "you have entered a different zone" feeling without
 * needing modal overlays. The sub-nav makes lateral admin navigation a single
 * click instead of bouncing through /admin/.
 */
export default function AdminLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <div className="admin-zone">
      <WarningBand message="◆ keeper's console · authorized holders only · the ritual is fragile ◆" />
      <AdminSubNav />
      <AuthGuard>{children}</AuthGuard>
      <WarningBand message="▒ each action is inscribed in the audit · move with intention ▒" />
    </div>
  );
}
