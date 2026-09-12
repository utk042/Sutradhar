import {getTranslations, setRequestLocale} from 'next-intl/server';
import HomeClient from './HomeClient';

/**
 * Officer home.
 *
 * Phase 1 renders the signed-in shell and the honest notice about sample data.
 * The upload action and pending list arrive in Phase 2, when there is something
 * behind them — a button that does nothing is worse than no button.
 */
export default async function HomePage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('home');
  const ta = await getTranslations('app');

  return (
    <section className="sutradhar-narrow ux4g-p-l">
      <h1 className="ux4g-heading-l-strong ux4g-mb-l">{t('title')}</h1>
      <HomeClient />
      <div className="ux4g-alert ux4g-alert-info ux4g-mt-l">
        <span className="ux4g-body-m-default">{t('phaseNotice')}</span>
      </div>
      <p className="ux4g-body-s-default ux4g-text-neutral-secondary ux4g-mt-l">
        {ta('sampleDataNotice')}
      </p>
    </section>
  );
}
