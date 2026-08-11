interface PaginationProps {
  page: number;
  pages: number;
  total: number;
  onPage: (page: number) => void;
}

function pageWindow(page: number, pages: number): number[] {
  const start = Math.max(1, page - 2);
  const end = Math.min(pages, start + 4);
  const list: number[] = [];
  for (let i = start; i <= end; i++) list.push(i);
  return list;
}

export default function Pagination({ page, pages, total, onPage }: PaginationProps) {
  if (pages <= 1) return null;
  const window = pageWindow(page, pages);

  return (
    <nav className="pagination" aria-label="Pagination">
      <button
        className="page-btn"
        disabled={page <= 1}
        onClick={() => onPage(page - 1)}
        aria-label="Previous page"
      >
        ←
      </button>
      {window[0] > 1 && (
        <>
          <button className="page-btn" onClick={() => onPage(1)}>
            1
          </button>
          {window[0] > 2 && <span className="page-ellipsis">…</span>}
        </>
      )}
      {window.map((p) => (
        <button
          key={p}
          className={`page-btn${p === page ? " current" : ""}`}
          onClick={() => onPage(p)}
          aria-current={p === page ? "page" : undefined}
        >
          {p}
        </button>
      ))}
      {window[window.length - 1] < pages && (
        <>
          {window[window.length - 1] < pages - 1 && <span className="page-ellipsis">…</span>}
          <button className="page-btn" onClick={() => onPage(pages)}>
            {pages}
          </button>
        </>
      )}
      <button
        className="page-btn"
        disabled={page >= pages}
        onClick={() => onPage(page + 1)}
        aria-label="Next page"
      >
        →
      </button>
      <span className="page-total">
        {total} article{total === 1 ? "" : "s"}
      </span>
    </nav>
  );
}
