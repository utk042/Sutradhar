import {getTranslations, setRequestLocale} from 'next-intl/server';
import LoginForm from './LoginForm';

export default async function LoginPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('login');

  return (
    <section className="sutradhar-narrow ux4g-p-l">
      <h1 className="ux4g-heading-l-strong ux4g-mb-s">{t('title')}</h1>
      <p className="ux4g-body-m-default ux4g-text-neutral-secondary ux4g-mb-l">{t('intro')}</p>
      <LoginForm />
    </section>
  );
}
