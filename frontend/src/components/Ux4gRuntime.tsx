'use client';

import {useEffect} from 'react';

/**
 * Initialises the UX4G runtime.
 *
 * The package's React guidance is a side-effect import of
 * `ux4g-web-components/design-system`, which injects the vendor scripts into the
 * page. That touches `document`, so it cannot run during server rendering — in
 * the App Router it has to sit in a client component behind an effect.
 *
 * `initRuntime()` is a no-op when window is unavailable and guards against
 * double-injection itself, so this is safe under Strict Mode's double render.
 *
 * The runtime provides the behaviours for Dropdown, Modal, Tooltip, Popover,
 * Accordion, Tab, Carousel, Drawer, Mega Menu and Alert. Every other component
 * is CSS-only and needs nothing here.
 */
export default function Ux4gRuntime() {
  useEffect(() => {
    let cancelled = false;
    import('ux4g-web-components/runtime').then(({initRuntime}) => {
      if (!cancelled) initRuntime();
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return null;
}
