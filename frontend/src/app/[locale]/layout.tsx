import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {NextIntlClientProvider} from 'next-intl';
import {getMessages, getTranslations, setRequestLocale} from 'next-intl/server';

import Ux4gRuntime from '@/components/Ux4gRuntime';
import Logo from '@/components/Logo';
import NavLinks from '@/components/NavLinks';
import LanguageSwitcher from '@/components/LanguageSwitcher';
import {routing, type Locale} from '@/i18n/routing';

// Order matters: the UX4G bundle declares the tokens our own sheet repoints, so
// it has to be imported first. The package's documented layer order is strict.
import 'ux4g-web-components/styles.css';
import '@/styles/app.css';

export async function generateMetadata({
  params
}: {
  params: Promise<{locale: string}>;
}): Promise<Metadata> {
  const {locale} = await params;
  const t = await getTranslations({locale, namespace: 'app'});
  return {title: `${t('name')} — ${t('tagline')}`, description: t('tagline')};
}

export function generateStaticParams() {
  return routing.locales.map((locale) => ({locale}));
}

/**
 * Sets `data-theme` before first paint.
 *
 * Design.md §10 requires `data-theme` on <html>; components have no fallback
 * theme. The UX4G runtime sets it on DOMContentLoaded, which is too late and
 * flashes.
 *
 * The attribute is deliberately NOT rendered server-side. The choice lives in
 * localStorage, which the server cannot see, so an SSR'd value would be wrong
 * for anyone who picked the other one — and rendering it would make this script
 * a no-op. Instead the script is synchronous and sits in <head>, so it runs
 * before the body paints: the officer's choice is in force on the first frame
 * and there is no flash of the wrong theme.
 *
 * Kept as a literal string rather than importing from lib/theme.ts: it has to
 * run before any bundle loads, so it cannot be part of one. The storage key
 * below is therefore written out twice; it must stay equal to
 * THEME_STORAGE_KEY in lib/theme.ts, or the settings screen writes a choice
 * this script never reads.
 */
const THEME_SCRIPT = `(function(){try{var c=window.localStorage.getItem('sutradhar.theme');var t=(c==='light'||c==='dark')?c:(window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light');document.documentElement.setAttribute('data-theme',t)}catch(e){document.documentElement.setAttribute('data-theme','light')}})();`;

export default async function LocaleLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  if (!routing.locales.includes(locale as Locale)) notFound();

  setRequestLocale(locale);
  const messages = await getMessages();
  const t = await getTranslations({locale, namespace: 'app'});
  const tf = await getTranslations({locale, namespace: 'footer'});

  return (
    <html lang={locale} suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{__html: THEME_SCRIPT}} />
      </head>
      <body>
        <NextIntlClientProvider messages={messages}>
          <div className="sutradhar-shell">
            <a className="sutradhar-skip-link ux4g-btn ux4g-btn-primary ux4g-btn-lg" href="#main">
              {t('skipToContent')}
            </a>

            <nav className="ux4g-navbar ux4g-navbar-desktop">
              {/* ux4g-navbar-wrap sets vertical padding only, so it needs a
                  container for the page gutter — otherwise the bar's contents
                  sit flush against the viewport edge. */}
              <div className="ux4g-container ux4g-navbar-wrap">
                <Logo />
                <div className="ux4g-navbar-right ux4g-d-flex ux4g-ai-center ux4g-gap-s">
                  <NavLinks />
                  <LanguageSwitcher />
                </div>
              </div>
            </nav>

            <main id="main">{children}</main>

            <footer className="sutradhar-footer">
              <div className="ux4g-container">
                <p className="ux4g-body-s-default ux4g-text-neutral-tertiary">
                  {tf('tagline')}
                </p>
              </div>
            </footer>
          </div>
          <Ux4gRuntime />
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
