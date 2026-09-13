'use client';

import {useCallback, useEffect, useId, useRef, useState} from 'react';
import {useTranslations} from 'next-intl';
import {Link, usePathname, useRouter} from '@/i18n/routing';
import {logout, me} from '@/lib/api';

/**
 * The service's navigation, at every width.
 *
 * **The bug this replaces.** The navbar carried `ux4g-navbar-desktop`, and the
 * shipped rule for that class is `@media (max-width:768px){ … display:none
 * !important }`. On a phone the entire bar — logo, links, Settings — was
 * removed from the page, so there was no way back to the desk, no way to the
 * office screen, and no way to Settings. That is the "no way back, no
 * dashboard" the brief calls out. UX4G's answer is the paired
 * `ux4g-navbar-mobile` slot, which this component finally provides.
 *
 * Desktop keeps the links in a row. Below 768px they move into a UX4G Drawer
 * opened by one clearly-labelled button — one tap to open, one to arrive, so
 * the "nothing more than two clicks" rule still holds.
 *
 * The menu button says the word "Menu" beside its icon rather than being an
 * icon alone. Our officers have not used a phone app like this before, and a
 * bare hamburger is learned, not obvious.
 *
 * Nothing here switches theme or language. Both are settings, and both live on
 * the Settings screen only — a control in the chrome of every page invites an
 * accidental change that the officer then cannot find their way back from.
 *
 * The role comes from the server, never from anything the browser holds: the
 * session is an httpOnly cookie and the role is not readable here. Hiding a
 * link is a courtesy — the routes refuse an officer regardless.
 *
 * Signed out, this renders nothing at all. The sign-in screen is meant to hold
 * the sign-in form and nothing else, and a link away from it is the one thing
 * that page must not offer.
 */

type Who = {full_name: string; role: 'officer' | 'dept_head'};

export default function SiteNav() {
  const t = useTranslations('nav');
  const ts = useTranslations('settings');
  const th = useTranslations('home');
  const pathname = usePathname();
  const router = useRouter();

  const [who, setWho] = useState<Who | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const menuId = useId();
  const drawerTitleId = useId();
  const openerRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    me().then((result) => {
      if (active) setWho(result.ok ? result.data : null);
    });
    return () => {
      active = false;
    };
  }, [pathname]);

  // Arriving on a new screen closes the menu; otherwise it stays open over the
  // page the officer just asked for.
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  const closeMenu = useCallback(() => {
    setMenuOpen(false);
    openerRef.current?.focus();
  }, []);

  /**
   * While the drawer is open it is the whole screen.
   *
   * - Escape closes it, and focus goes back to the button that opened it. An
   *   officer who opens the menu by accident must not be stranded in it.
   * - The page behind it does not scroll. `ux4g-drawer-lock` is UX4G's own body
   *   class for exactly that.
   * - Tab cycles inside the drawer rather than walking off into the page
   *   underneath. The drawer is `aria-modal`, and a modal that a keyboard can
   *   tab out of is lying about what it is: the officer would be typing into a
   *   page they cannot see behind an overlay.
   * - Focus lands on the panel itself, not on its first button, so a screen
   *   reader announces what has just opened before it announces a control.
   */
  useEffect(() => {
    if (!menuOpen) return;

    const drawer = drawerRef.current;
    document.body.classList.add('ux4g-drawer-lock');
    drawer?.focus();

    function focusable(): HTMLElement[] {
      if (!drawer) return [];
      return Array.from(
        drawer.querySelectorAll<HTMLElement>('a[href], button:not([disabled])')
      ).filter((element) => element.getClientRects().length > 0);
    }

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        closeMenu();
        return;
      }
      if (event.key !== 'Tab' || !drawer) return;

      const stops = focusable();
      if (stops.length === 0) return;

      const first = stops[0];
      const last = stops[stops.length - 1];
      const active = document.activeElement;

      if (!drawer.contains(active)) {
        event.preventDefault();
        (event.shiftKey ? last : first).focus();
      } else if (event.shiftKey && (active === first || active === drawer)) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
        event.preventDefault();
        first.focus();
      }
    }

    document.addEventListener('keydown', onKeyDown);

    return () => {
      document.body.classList.remove('ux4g-drawer-lock');
      document.removeEventListener('keydown', onKeyDown);
    };
  }, [menuOpen, closeMenu]);

  async function signOut() {
    setMenuOpen(false);
    await logout();
    router.replace('/login');
  }

  if (who === null) return null;

  // Both roles get the dashboard link; it goes to the same address and renders
  // the screen that belongs to the caller. Only the wording differs, because
  // "Your office" would be a promise the officer's screen does not keep — it
  // shows their own desk counted, not anybody else's.
  const links = [
    {href: '/', label: t('desk')},
    {
      href: '/dashboard',
      label: who.role === 'dept_head' ? t('dashboard') : t('work')
    },
    {href: '/settings', label: ts('open')}
  ];

  return (
    <>
      {/* Wide screens: the links in a row. */}
      <div className="ux4g-navbar-desktop ux4g-d-flex ux4g-ai-center ux4g-gap-s">
        <ul className="ux4g-navbar-links">
          {links.map((link) => (
            <li key={link.href}>
              <Link
                href={link.href}
                className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
                aria-current={pathname === link.href ? 'page' : undefined}
              >
                {link.label}
              </Link>
            </li>
          ))}
        </ul>
        <button
          type="button"
          className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
          onClick={signOut}
        >
          {th('signOut')}
        </button>
      </div>

      {/* Narrow screens: one button, and everything behind it. */}
      <div className="ux4g-navbar-mobile">
        <button
          ref={openerRef}
          type="button"
          className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg"
          aria-expanded={menuOpen}
          aria-controls={menuId}
          onClick={() => setMenuOpen(true)}
        >
          {t('menu')}
        </button>
      </div>

      {/* The drawer itself lives outside both slots so the navbar's own
          overflow and stacking rules cannot clip it. It stays in the DOM when
          closed — UX4G animates it in and out with a transform, and removing it
          would make it appear without the transition. `inert` keeps its links
          out of the tab order and away from screen readers while it is shut. */}
      <div
        className={`ux4g-drawer-overlay sutradhar-menu-overlay${
          menuOpen ? ' ux4g-drawer-open' : ''
        }`}
        onClick={closeMenu}
        aria-hidden="true"
      />
      <div
        ref={drawerRef}
        id={menuId}
        className={`ux4g-drawer ux4g-drawer-right sutradhar-menu-drawer${
          menuOpen ? ' ux4g-drawer-open' : ''
        }`}
        role="dialog"
        aria-modal={menuOpen || undefined}
        aria-labelledby={drawerTitleId}
        inert={!menuOpen}
        tabIndex={-1}
      >
        <div className="ux4g-drawer-header">
          <div className="ux4g-drawer-title-group">
            <div className="ux4g-drawer-title-wrapper">
              <h2 id={drawerTitleId} className="ux4g-drawer-title">
                {t('menu')}
              </h2>
            </div>
            <span className="ux4g-drawer-subtitle">
              {th('signedInAs', {name: who.full_name})}
            </span>
          </div>
          <div className="ux4g-drawer-header-actions">
            <button
              type="button"
              className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg"
              onClick={closeMenu}
            >
              {t('closeMenu')}
            </button>
          </div>
        </div>

        <div className="ux4g-drawer-body">
          <ul className="sutradhar-list-reset sutradhar-menu-list">
            {links.map((link) => (
              <li key={link.href}>
                <Link
                  href={link.href}
                  className="ux4g-btn ux4g-btn-text-neutral ux4g-btn-lg ux4g-w-100"
                  aria-current={pathname === link.href ? 'page' : undefined}
                  onClick={() => setMenuOpen(false)}
                >
                  {link.label}
                </Link>
              </li>
            ))}
          </ul>
        </div>

        <div className="ux4g-drawer-footer">
          <button
            type="button"
            className="ux4g-btn ux4g-btn-outline-neutral ux4g-btn-lg ux4g-w-100"
            onClick={signOut}
          >
            {th('signOut')}
          </button>
        </div>
      </div>
    </>
  );
}
