import type {Metadata} from 'next';
import {notFound} from 'next/navigation';
import {NextIntlClientProvider} from 'next-intl';
import {getMessages, getTranslations, setRequestLocale} from 'next-intl/server';

import Ux4gRuntime from '@/components/Ux4gRuntime';
import Logo from '@/components/Logo';
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
 * The attribute is deliberately NOT rendered server-side: an SSR'd
 * `data-theme="light"` would make this script a no-op and the service would be
 * stuck in light mode regardless of the officer's system setting. The script is
 * synchronous and sits in <head>, so it runs before the body paints and there is
 * no flash. Dark mode then comes free from the system preference, with no toggle
 * of our own — per the brief.
 */
const THEME_SCRIPT = `(function(){try{var d=document.documentElement;if(!d.getAttribute('data-theme')){d.setAttribute('data-theme',window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light')}}catch(e){document.documentElement.setAttribute('data-theme','light')}})();`;

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
