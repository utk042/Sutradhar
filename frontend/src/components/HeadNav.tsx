'use client';

import {useEffect, useState} from 'react';
import {useTranslations} from 'next-intl';
import {Link, usePathname} from '@/i18n/routing';
import {me} from '@/lib/api';

/**
 * The link to the dashboard, shown only to a head of department.
 *
 * Asked of the server rather than inferred from anything the browser holds —
 * the session is an httpOnly cookie and the role is not readable here. Hiding
 * the link is a courtesy, not the control: the routes refuse an officer
 * regardless.
 */
export default function HeadNav() {
  const t = useTranslations('nav');
  const pathname = usePathname();
  const [isHead, setIsHead] = useState(false);

  useEffect(() => {
    let active = true;
    me().then((who) => {
      if (active) setIsHead(who.ok && who.data.role === 'dept_head');
    });
  }, [pathname]);

  if (!isHead) return null;

  return (
    <>
      <Link href="/" className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg">
        {t('desk')}
      </Link>
      <Link href="/dashboard" className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg">
        {t('dashboard')}
      </Link>
    </>
  );
}
