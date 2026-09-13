/**
 * Choosing light or dark.
 *
 * UX4G ships both palettes and switches on `data-theme` on the root element, so
 * this only decides which of the two is in force. Three choices, because
 * "match my device" is what most people actually want and neither of the other
 * two expresses it.
 *
 * The preference is per browser, in localStorage. It is a display setting, not
 * a fact about the officer: they may reasonably want dark at home and light on
 * the office machine, and storing it on the account would make one override the
 * other. Every read and write is guarded — a locked-down profile throws rather
 * than returning null, and a settings screen that crashes the page is worse
 * than one that forgets.
 */

export type ThemeChoice = 'light' | 'dark' | 'system';

export const THEME_STORAGE_KEY = 'sutradhar.theme';

export function readThemeChoice(): ThemeChoice {
  try {
    const stored = window.localStorage.getItem(THEME_STORAGE_KEY);
    if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
  } catch {
    /* storage unavailable — fall through to the default */
  }
  return 'system';
}

export function resolveTheme(choice: ThemeChoice): 'light' | 'dark' {
  if (choice !== 'system') return choice;
  try {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  } catch {
    return 'light';
  }
}

export function applyThemeChoice(choice: ThemeChoice): void {
  document.documentElement.setAttribute('data-theme', resolveTheme(choice));
  try {
    window.localStorage.setItem(THEME_STORAGE_KEY, choice);
  } catch {
    /* storage unavailable — the change still applies for this visit */
  }
}

/**
 * Follow the device while "match my device" is selected.
 *
 * Without this, someone whose machine switches to dark at sunset keeps a light
 * page until they reload. Returns its own unsubscribe.
 */
export function watchSystemTheme(onChange: () => void): () => void {
  try {
    const query = window.matchMedia('(prefers-color-scheme: dark)');
    query.addEventListener('change', onChange);
    return () => query.removeEventListener('change', onChange);
  } catch {
    return () => {};
  }
}
