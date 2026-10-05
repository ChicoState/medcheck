import { FormEvent, useState } from "react";

type OpenPanel = "menu" | "account" | null;

export function App() {
  const [query, setQuery] = useState("");
  const [submittedQuery, setSubmittedQuery] = useState("");
  const [openPanel, setOpenPanel] = useState<OpenPanel>(null);

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmedQuery = query.trim();

    if (trimmedQuery) {
      setSubmittedQuery(trimmedQuery);
    }
  }

  return (
    <main className="landing-page">
      <nav className="top-bar" aria-label="Primary navigation">
        <button
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
          onClick={() =>
            setOpenPanel(openPanel === "account" ? null : "account")
          }
        >
          <svg aria-hidden="true" viewBox="0 0 24 24">
            <path d="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm7 8a7 7 0 0 0-14 0h14Z" />
          </svg>
        </button>

        {openPanel === "menu" && (
          <div className="popover menu-panel" id="menu-panel">
            <p className="popover-title">Menu</p>
            <button type="button" onClick={() => setOpenPanel(null)}>
              Search
            </button>
          </div>
        )}

        {openPanel === "account" && (
          <div className="popover account-panel" id="account-panel">
            <p className="popover-title">Account</p>
            <button type="button" onClick={() => setOpenPanel(null)}>
              Sign in
            </button>
          </div>
        )}
      </nav>

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
    </main>
  );
}
