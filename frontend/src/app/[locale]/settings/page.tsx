import {getTranslations, setRequestLocale} from 'next-intl/server';
import Breadcrumb from '@/components/Breadcrumb';
import SettingsClient from './SettingsClient';

export default async function SettingsPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('settings');
  const tn = await getTranslations('nav');

  return (
    <section className="sutradhar-narrow ux4g-p-l">
      <Breadcrumb
        label={tn('breadcrumb')}
        items={[{label: tn('desk'), href: '/'}, {label: t('title')}]}
      />
      <h1 className="ux4g-heading-l-strong ux4g-mb-xs">{t('title')}</h1>
      <p className="ux4g-body-m-default ux4g-text-neutral-secondary ux4g-mb-l">
        {t('subtitle')}
      </p>
      <SettingsClient />
    </section>
  );
}
