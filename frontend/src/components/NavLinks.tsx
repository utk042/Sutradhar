'use client';

import {useEffect, useState} from 'react';
import {useTranslations} from 'next-intl';
import {Link, usePathname} from '@/i18n/routing';
import {me} from '@/lib/api';

/**
 * The navigation links: settings once signed in, the office for a head.
 *
 * The role is asked of the server rather than inferred from anything the
 * browser holds — the session is an httpOnly cookie and the role is not
 * readable here. Hiding a link is a courtesy, not the control: the routes
 * refuse an officer regardless.
 *
 * Nothing shows before sign-in. The brief asks for a login screen with nothing
 * on it but the sign-in form, and a Settings link there would also be a link
 * away from the only thing that page is for.
 */
export default function NavLinks() {
  const t = useTranslations('nav');
  const ts = useTranslations('settings');
  const pathname = usePathname();
  const [role, setRole] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    me().then((who) => {
      if (active) setRole(who.ok ? who.data.role : null);
    });
    return () => {
      active = false;
    };
  }, [pathname]);

  if (role === null) return null;

  return (
    <>
      {role === 'dept_head' && (
        <>
          <Link href="/" className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg">
            {t('desk')}
          </Link>
          <Link href="/dashboard" className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg">
            {t('dashboard')}
          </Link>
        </>
      )}
      <Link href="/settings" className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg">
        {ts('open')}
      </Link>
    </>
  );
}
