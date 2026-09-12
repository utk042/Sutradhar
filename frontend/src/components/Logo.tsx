/**
 * The Sutradhar logo: mark plus wordmark, as one lockup.
 *
 * A sūtradhāra is the one who holds the thread — the stage-manager of a Sanskrit
 * play, who ties the parts into a whole without performing it. The mark is that
 * thread drawn as an S, with a bead at the tail where it is held. It is the
 * product's job: gather the separate checks, hold them, hand them to a person.
 *
 * Drawn with `currentColor`, so it takes the surrounding text colour and works
 * in both themes from one asset. Strokes on a transparent ground, with no
 * knocked-out counters — UX4G applies `filter: brightness(0) invert(1)` to
 * `.ux4g-navbar-logo` in dark mode, which collapses every opaque pixel to white,
 * so the mark has to read as a silhouette.
 *
 * The wordmark is live SVG text in Noto Sans SemiBold, the UX4G typeface, rather
 * than outlined paths: it stays crisp at any size and remains real text for
 * search and selection. `role="img"` with a label means a screen reader
 * announces the product name once, not the letter S and the word separately.
 *
 * Sizing comes from `.ux4g-navbar-logo` (height 2.5rem, width auto), which is
 * the navbar's own logo slot — no size is set here.
 */
export default function Logo() {
  return (
    <svg
      viewBox="0 0 138 32"
      fill="none"
      role="img"
      aria-label="Sutradhar"
      className="ux4g-navbar-logo sutradhar-logo"
    >
      <path
        d="M23.8 10.4C22.7 7.4 19.6 5.6 16 5.6c-3.9 0-6.8 2-6.8 5 0 6 13.7 3.4 13.7 10.6 0 3.5-3.3 5.6-7.3 5.6-3.2 0-6-1.2-7.2-3.4"
        stroke="currentColor"
        strokeWidth="3.4"
        strokeLinecap="round"
      />
      <circle cx="8.6" cy="23.6" r="3.2" fill="currentColor" />
      <text
        x="42"
        y="22.6"
        fontFamily="'Noto Sans', system-ui, sans-serif"
        fontSize="20"
        fontWeight="600"
        letterSpacing="0.1"
        fill="currentColor"
      >
        Sutradhar
      </text>
    </svg>
  );
}
