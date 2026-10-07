import { FormEvent, useEffect, useRef, useState } from "react";
import { Navigate, NavLink, Route, Routes } from "react-router-dom";

type OpenPanel = "menu" | "account" | null;

export type SavedMedicine = {
  id: string;
  name: string;
};

type AppProps = {
  isAuthenticated?: boolean;
  savedMedicines?: SavedMedicine[];
};

function Navigation({ isAuthenticated }: { isAuthenticated: boolean }) {
  const [openPanel, setOpenPanel] = useState<OpenPanel>(null);
  const menuButtonRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (openPanel !== "menu") {
      return;
    }

    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";

    function closeMenu(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpenPanel(null);
        menuButtonRef.current?.focus();
      }
    }

    document.addEventListener("keydown", closeMenu);
    return () => {
      document.removeEventListener("keydown", closeMenu);
      document.body.style.overflow = previousOverflow;
    };
  }, [openPanel]);

  return (
    <header className="top-bar">
      <button
        ref={menuButtonRef}
        className="icon-button"
        type="button"
        aria-label="Open menu"
        aria-expanded={openPanel === "menu"}
        aria-controls="menu-panel"
        onClick={() => setOpenPanel(openPanel === "menu" ? null : "menu")}
      >
        <span className="hamburger-icon" aria-hidden="true">
          <span />
          <span />
          <span />
        </span>
      </button>
      <button
        className="icon-button"
        type="button"
        aria-label="Account"
        aria-expanded={openPanel === "account"}
        aria-controls="account-panel"
        onClick={() => setOpenPanel(openPanel === "account" ? null : "account")}
      >
        <svg aria-hidden="true" viewBox="0 0 24 24">
          <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm7 8a7 7 0 0 0-14 0h14Z" />
        </svg>
      </button>

      {openPanel === "menu" && (
        <button
          className="drawer-backdrop"
          type="button"
          aria-label="Close menu"
          onClick={() => setOpenPanel(null)}
        />
      )}

      <nav
        className="menu-drawer"
        id="menu-panel"
        aria-label="Menu"
        aria-hidden={openPanel !== "menu"}
        data-open={openPanel === "menu"}
      >
        <p className="popover-title">Navigation</p>
        <NavLink to="/" end onClick={() => setOpenPanel(null)}>
          Home
        </NavLink>
        {isAuthenticated && (
          <NavLink to="/saved-medicines" onClick={() => setOpenPanel(null)}>
            Saved Medicines
          </NavLink>
        )}
      </nav>

      {openPanel === "account" && (
        <div className="popover account-panel" id="account-panel">
          <p className="popover-title">Account</p>
          <button type="button" onClick={() => setOpenPanel(null)}>
            Sign in
          </button>
        </div>
      )}
    </header>
  );
}

function HomePage() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();

    if (trimmedQuery) {
      setSubmittedQuery(trimmedQuery);
    }
  }

  return (
    <section className="search-panel" aria-labelledby="page-title">
      <h1 id="page-title">MedCheck</h1>
      <p className="tagline">
        Your simple starting point for health information.
      </p>

      <form className="search-form" role="search" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="health-search">
          Search medications, symptoms, or health topics
        </label>
        <input
          id="health-search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search medications, symptoms, or health topics"
          autoComplete="off"
        />
        <button type="submit" aria-label="Search">
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="m20 20-4.35-4.35m1.35-5.15a6.5 6.5 0 1 1-13 0 6.5 6.5 0 0 1 13 0Z" />
          </svg>
        </button>
      </form>

      <p className="search-status" role="status" aria-live="polite">
        {submittedQuery ? `Searching for “${submittedQuery}”` : ""}
      </p>
    </section>
  );
}

function SavedMedicinesPage({ medicines }: { medicines: SavedMedicine[] }) {
  return (
    <section className="saved-medicines" aria-labelledby="saved-page-title">
      <div className="saved-medicines-heading">
        <p className="section-label">Your library</p>
        <h1 id="saved-page-title">Saved Medicines</h1>
        <p>Medicines you save will be collected here for quick reference.</p>
      </div>

      {medicines.length === 0 ? (
        <div className="empty-state">
          <span className="empty-state-icon" aria-hidden="true">
            +
          </span>
          <h2>No saved medicines yet.</h2>
          <p>Return Home to search when you are ready to build your list.</p>
          <NavLink className="home-link" to="/">
            Return Home
          </NavLink>
        </div>
      ) : (
        <ul className="medicine-list">
          {medicines.map((medicine) => (
            <li key={medicine.id}>{medicine.name}</li>
          ))}
        </ul>
      )}
    </section>
  );
}

export function App({
  isAuthenticated = false,
  savedMedicines = [],
}: AppProps) {
  return (
    <main className="app-shell">
      <Navigation isAuthenticated={isAuthenticated} />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/saved-medicines"
          element={
            isAuthenticated ? (
              <SavedMedicinesPage medicines={savedMedicines} />
            ) : (
              <Navigate to="/" replace />
            )
          }
        />
      </Routes>
    </main>
  );
}
