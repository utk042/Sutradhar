import {getTranslations, setRequestLocale} from 'next-intl/server';
import HomeClient from './HomeClient';

/**
 * Officer home.
 *
 * One action — upload — and the list of documents waiting for a decision.
 * Nothing else, per the brief.
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
    <section className="sutradhar-page ux4g-p-l">
      <h1 className="ux4g-heading-l-strong ux4g-mb-l">{t('title')}</h1>
      <HomeClient />
      <p className="ux4g-body-s-default ux4g-text-neutral-tertiary ux4g-mt-xl">
        {ta('sampleDataNotice')}
      </p>
    </section>
  );
}
