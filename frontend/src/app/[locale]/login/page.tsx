import {getTranslations, setRequestLocale} from 'next-intl/server';
import AuthArtwork from '@/components/AuthArtwork';
import LoginForm from './LoginForm';

/**
 * Sign in.
 *
 * Two halves on a wide screen: the form on one side, a picture of what the
 * service does on the other. One column on a phone.
 *
 * The form comes first in the document, not the picture. Whatever the eye does,
 * a keyboard or a screen reader starts at the top of the page — so the first
 * thing either reaches is the mobile-number field, and the artwork sits after
 * the only thing this page is for. On a narrow screen that same order is also
 * the right visual one: the form is above the fold and the picture follows it,
 * rather than a decorative panel pushing the sign-in button off the screen.
 *
 * The picture is placed into the left column by the grid, not by the markup.
 */
export default async function LoginPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('login');

  return (
    <div className="sutradhar-auth ux4g-p-l">
      <div className="sutradhar-auth-split">
        <section className="sutradhar-auth-form" aria-labelledby="sign-in">
          <h1 id="sign-in" className="ux4g-heading-l-strong ux4g-mb-s">
            {t('title')}
          </h1>
          <p className="ux4g-body-m-default ux4g-text-neutral-secondary ux4g-mb-l">
            {t('intro')}
          </p>
          <LoginForm />
        </section>

        <aside className="sutradhar-auth-visual">
          <AuthArtwork />
          {/* Its own line, not the footer's. The footer carries the same
              promise on every screen, and printing it twice on one page makes
              it read as a slogan rather than as a description of what happens. */}
          <p className="ux4g-heading-s-strong sutradhar-auth-promise">
            {t('visualTitle')}
          </p>
          <p className="ux4g-body-s-default sutradhar-auth-caption">{t('visualCaption')}</p>
        </aside>
      </div>
    </div>
  );
}
