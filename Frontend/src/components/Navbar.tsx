import { useState, type FormEvent } from "react";
import { Link, NavLink, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { initials } from "../utils";

const navLinkClass = ({ isActive }: { isActive: boolean }) =>
  `nav-link${isActive ? " active" : ""}`;

export default function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [query, setQuery] = useState("");

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    const q = query.trim();
    navigate(q ? `/search?q=${encodeURIComponent(q)}` : "/");
    setQuery("");
  }

  return (
    <header className="navbar">
      <div className="container navbar-inner">
        <Link to="/" className="brand">
          <span className="brand-mark" aria-hidden="true">
            N
          </span>
          <span className="brand-name">
            News<span className="brand-accent">Hub</span>
          </span>
        </Link>

        <nav className="nav-links" aria-label="Main navigation">
          <NavLink to="/" end className={navLinkClass}>
            Home
          </NavLink>
          <NavLink to="/browse" className={navLinkClass}>
            Browse
          </NavLink>
          {user && (
            <NavLink to="/bookmarks" className={navLinkClass}>
              Bookmarks
            </NavLink>
          )}
        </nav>

        <form className="search-form" onSubmit={onSubmit} role="search">
          <svg
            className="search-icon"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            aria-hidden="true"
          >
            <circle cx="11" cy="11" r="7" />
            <path d="m21 21-4.3-4.3" strokeLinecap="round" />
          </svg>
          <input
            type="search"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search the news…"
            aria-label="Search articles"
          />
        </form>

        <div className="nav-auth">
          {user ? (
            <div className="user-chip">
              <span className="avatar" aria-hidden="true">
                {initials(user.full_name ?? user.username)}
              </span>
              <span className="user-name">{user.full_name ?? user.username}</span>
              <button className="link-button" onClick={logout}>
                Log out
              </button>
            </div>
          ) : (
            <>
              <Link to="/login" className="btn btn-ghost">
                Log in
              </Link>
              <Link to="/register" className="btn btn-primary">
                Sign up
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
}
