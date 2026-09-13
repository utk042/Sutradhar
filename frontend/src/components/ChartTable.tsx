/**
 * The numbers behind a chart, as a table.
 *
 * Not a fallback — a second way in. A screen reader gets the figures with their
 * labels attached rather than a row of bare numbers; anyone who reads numbers
 * faster than shapes gets them directly; and the copy-and-paste that always
 * follows a chart has something to copy. Closed by default so it does not crowd
 * a screen whose point is the picture.
 *
 * `tabular-nums` belongs here and nowhere else on these screens: a column of
 * figures has to align vertically, which is exactly what it is for.
 */
export default function ChartTable({
  caption,
  head,
  rows,
  label
}: {
  caption: string;
  head: string[];
  /** First cell of each row is its heading. */
  rows: string[][];
  label: string;
}) {
  return (
    <details className="sutradhar-chart-table ux4g-mt-m">
      <summary className="ux4g-body-s-default">{label}</summary>
      <div className="sutradhar-table-scroll ux4g-mt-xs">
        <table className="ux4g-table ux4g-table-s ux4g-w-100">
          <caption className="sutradhar-sr-only">{caption}</caption>
          <thead>
            <tr>
              {head.map((cell) => (
                <th key={cell} scope="col">
                  {cell}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row[0]}>
                <th scope="row" className="ux4g-table-cell-text">
                  {row[0]}
                </th>
                {row.slice(1).map((cell, index) => (
                  <td
                    key={index}
                    className="ux4g-table-cell-text sutradhar-figures"
                  >
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </details>
  );
}
