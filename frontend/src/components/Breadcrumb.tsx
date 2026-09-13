import {Link} from '@/i18n/routing';

/**
 * The trail back.
 *
 * Every screen except the desk and the sign-in page carries one, so there is
 * always a way back that does not depend on the browser's Back button — an
 * officer who arrived by typing a URL, or who has been reading a document for
 * ten minutes, has no reason to trust Back and often will not find it on a
 * phone.
 *
 * UX4G ships Breadcrumb (`ux4g-breadcrumb` + `ux4g-breadcrumb-divider`), which
 * draws the "›" separators itself from `.ux4g-breadcrumb-item + .ux4g-breadcrumb-item`.
 * The shipped `.ux4g-breadcrumb-list` rule sets `flex-wrap` and `gap` but never
 * `display`, so the gap is inert on a bare list; the UX4G flex utilities supply
 * it rather than a custom rule, and `sutradhar-list-reset` removes the browser's
 * list indent.
 *
 * Semantics: an ordered list inside a named `<nav>`, with `aria-current="page"`
 * on the final crumb. The last crumb is text, not a link — a link to the page
 * you are already on is a trap for anyone navigating by keyboard.
 */

export type Crumb = {
  label: string;
  /** Omitted on the last crumb, which is the page you are already on. */
  href?: string;
};

export default function Breadcrumb({
  items,
  label
}: {
  items: Crumb[];
  /** Names the landmark, e.g. "Breadcrumb". Required — there may be several navs. */
  label: string;
}) {
  return (
    <nav
      aria-label={label}
      className="ux4g-breadcrumb ux4g-breadcrumb-divider sutradhar-breadcrumb ux4g-mb-m"
    >
      <ol className="ux4g-breadcrumb-list sutradhar-list-reset ux4g-d-flex ux4g-ai-center">
        {items.map((item, index) => {
          const last = index === items.length - 1;
          return (
            <li
              key={`${item.label}-${index}`}
              className={`ux4g-breadcrumb-item${last ? ' active' : ''}`}
            >
              {last || !item.href ? (
                <span aria-current={last ? 'page' : undefined}>{item.label}</span>
              ) : (
                <Link className="ux4g-breadcrumb-link" href={item.href}>
                  {item.label}
                </Link>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
