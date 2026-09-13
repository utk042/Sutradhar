'use client';

import {useEffect, useState} from 'react';
import {useRouter} from '@/i18n/routing';
import DepartmentDashboard from './DepartmentDashboard';
import OfficerWork from './OfficerWork';
import {me} from '@/lib/api';

/**
 * One address, two screens.
 *
 * A head of department gets the office: the numbers for everybody, the roster,
 * the audit trail, the model switch. An officer gets their own desk counted —
 * what is waiting for them, what they decided, how long they take — and none of
 * the office-wide things, which the server refuses them in any case.
 *
 * Both live at `/dashboard` rather than at two addresses, so the navigation bar
 * carries one link and neither role has to learn where the other's screen is.
 * The label on that link differs; the place it goes does not.
 *
 * The role is asked of the server. It is not in anything the browser can read —
 * the session is an httpOnly cookie — and even if it were, choosing a screen
 * from a client-held claim is choosing a screen from something the client could
 * change. Nothing here is a permission check: it decides which of two screens to
 * draw, and every route behind either one re-checks the role for itself.
 */
export default function DashboardClient() {
  const router = useRouter();
  const [role, setRole] = useState<'officer' | 'dept_head' | null>(null);

  useEffect(() => {
    let active = true;
    me().then((who) => {
      if (!active) return;
      if (who.ok) setRole(who.data.role);
      else router.replace('/login');
    });
    return () => {
      active = false;
    };
  }, [router]);

  if (role === null) return null;
  return role === 'dept_head' ? <DepartmentDashboard /> : <OfficerWork />;
}
