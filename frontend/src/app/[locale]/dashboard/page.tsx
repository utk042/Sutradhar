import {setRequestLocale} from 'next-intl/server';
import DashboardClient from './DashboardClient';

export default async function DashboardPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  return <DashboardClient />;
}
