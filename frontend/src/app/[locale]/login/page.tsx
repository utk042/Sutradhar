import {getTranslations, setRequestLocale} from 'next-intl/server';
import AuthArtwork from '@/components/AuthArtwork';
import LoginForm from './LoginForm';

/**
 * Sign in.
 *
 * The whole thing sits in one card — a split panel, tinted on the illustration
 * side and plain on the form side — so the page reads as a single object on a
 * desk rather than as two things floating on a background. One box at every
 * width, as asked.
 *
 * **Document order is visual order, in both layouts.** The illustration comes
 * first in the markup: on a phone that puts it at the top, which is what it
 * should be, and on a wide screen the grid's natural order puts it in the left
 * column, which is also where it should be. Nothing is repositioned by CSS
 * against the order it is written in, so a screen reader and a sighted reader
 * meet the same things in the same sequence — which `grid-row` tricks would
 * have quietly broken.
 *
 * The drawing itself is `aria-hidden` and says nothing the caption beside it
 * does not, so the two short lines before the form cost a screen-reader user
 * very little, and the skip link at the top of every page costs them nothing.
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
      <div className="ux4g-card ux4g-card-outline sutradhar-auth-card">
        <div className="sutradhar-auth-split">
          <aside className="sutradhar-auth-visual">
            <AuthArtwork />
            {/* Its own line, not the footer's. The footer carries the same
                promise on every screen, and printing it twice on one page makes
                it read as a slogan rather than as a description of what
                happens. */}
            <p className="ux4g-heading-s-strong sutradhar-auth-promise">
              {t('visualTitle')}
            </p>
            <p className="ux4g-body-s-default sutradhar-auth-caption">
              {t('visualCaption')}
            </p>
          </aside>

          <section className="sutradhar-auth-form" aria-labelledby="sign-in">
            <h1 id="sign-in" className="ux4g-heading-l-strong ux4g-mb-s">
              {t('title')}
            </h1>
            <p className="ux4g-body-m-default ux4g-text-neutral-secondary ux4g-mb-l">
              {t('intro')}
            </p>
            <LoginForm />
          </section>
        </div>
      </div>
    </div>
  );
}
