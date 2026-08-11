export default function Footer() {
  return (
    <footer className="footer">
      <div className="container footer-inner">
        <p>
          <strong>NewsHub</strong> — a news discovery &amp; management platform.
        </p>
        <p className="footer-meta">
          Built with React, Vite &amp; FastAPI · Seeded demo content · API docs at{" "}
          <a href="http://127.0.0.1:8000/docs" target="_blank" rel="noreferrer">
            /docs
          </a>
        </p>
      </div>
    </footer>
  );
}
