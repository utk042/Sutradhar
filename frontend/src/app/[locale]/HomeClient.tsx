'use client';

import {useEffect, useState} from 'react';
import {useTranslations} from 'next-intl';
import {useRouter} from '@/i18n/routing';
import {logout, me, type CurrentUser} from '@/lib/api';

/**
 * Shows who is signed in and offers sign-out.
 *
 * The session is an httpOnly cookie, so the only way to learn who is signed in
 * is to ask the server. An unauthenticated answer sends the officer to sign-in
 * rather than showing an empty screen.
 */
export default function HomeClient() {
  const t = useTranslations('home');
  const router = useRouter();
  const [user, setUser] = useState<CurrentUser | null>(null);

  useEffect(() => {
    let active = true;
    me().then((result) => {
      if (!active) return;
      if (result.ok) setUser(result.data);
      else router.replace('/login');
    });
    return () => {
      active = false;
    };
  }, [router]);

  if (user === null) return null;

  return (
    <div className="ux4g-d-flex ux4g-ai-center ux4g-jc-between ux4g-gap-m">
      <p className="ux4g-body-m-default">{t('signedInAs', {name: user.full_name})}</p>
      <button
        type="button"
        className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
        onClick={async () => {
          await logout();
          router.replace('/login');
        }}
      >
        {t('signOut')}
      </button>
    </div>
  );
}
