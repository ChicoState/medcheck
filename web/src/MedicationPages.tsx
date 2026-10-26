import { FormEvent, useEffect, useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { Account } from "./auth";
import {
  MedicationDetail,
  MedicationSummary,
  Page,
  SavedMedication,
  MedicationSchedule,
  currentMedicationSchedule,
  medicationDetail,
  removeMedication,
  saveMedication,
  savedMedications,
  searchMedications,
} from "./medications";

function message(error: unknown) {
  return error instanceof Error ? error.message : "Please try again.";
}

function WeeklyOrganizer() {
  const [selectedDay, setSelectedDay] = useState("Monday");
  const [schedule, setSchedule] = useState<MedicationSchedule | null>(null);
  const [error, setError] = useState("");
  const monday = new Date();
  const dayOfWeek = monday.getDay();
  monday.setDate(monday.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1));
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(monday);
    date.setDate(monday.getDate() + index);
    return {
      name: date.toLocaleDateString("en-US", { weekday: "long" }),
      number: date.getDate(),
    };
  });

  useEffect(() => {
    currentMedicationSchedule().then(setSchedule, (reason) => {
      setError(message(reason));
    });
  }, []);

  const selectedMedicines = schedule?.[selectedDay] ?? [];

  return (
    <section className="weekly-organizer" aria-labelledby="organizer-title">
      <div className="organizer-heading">
        <div>
          <p className="section-label">Plan ahead</p>
          <h2 id="organizer-title">Weekly organizer</h2>
        </div>
        <span className="organizer-caption">Tap a day to open</span>
      </div>
      {error && (
        <p className="page-error" role="alert">
          {error}
        </p>
      )}
      <div className="organizer" role="group" aria-label="Medication week">
        {days.map((day) => {
          const doses = schedule?.[day.name] ?? [];
          return (
            <button
              className="organizer-day"
              type="button"
              key={day.name}
              aria-label={`${day.name} ${day.number}`}
              aria-pressed={selectedDay === day.name}
              onClick={() => setSelectedDay(day.name)}
            >
              <span className="organizer-day-name">{day.name.slice(0, 3)}</span>
              <span className="organizer-day-number">{day.number}</span>
              <span className="pill-compartment" aria-hidden="true">
                {doses.length > 0 ? (
                  doses
                    .slice(0, 3)
                    .map((dose) => <span className="pill" key={dose.id} />)
                ) : (
                  <span className="pill-empty" />
                )}
              </span>
              <span className="sr-only">
                {doses.length} medication{" "}
                {doses.length === 1 ? "dose" : "doses"}
              </span>
            </button>
          );
        })}
      </div>
      <div className="organizer-details" aria-live="polite">
        <div className="organizer-details-heading">
          <p className="section-label">Open compartment</p>
          <h3>{selectedDay}&apos;s medicines</h3>
        </div>
        {selectedMedicines.length > 0 ? (
          <ul className="dose-list">
            {selectedMedicines.map((medicine) => (
              <li className="dose-card" key={medicine.id}>
                <span className="dose-icon" aria-hidden="true" />
                <span className="dose-copy">
                  <strong>{medicine.name}</strong>
                  <span>{medicine.time}</span>
                </span>
                <span className={`food-badge ${medicine.food}`}>
                  {medicine.food === "with food"
                    ? "Take with food"
                    : "Take without food"}
                </span>
              </li>
            ))}
          </ul>
        ) : (
          <p className="organizer-empty">
            No medicines scheduled for this day.
          </p>
        )}
      </div>
    </section>
  );
}

function MedicineLink({ medicine }: { medicine: MedicationSummary }) {
  return (
    <Link to={`/medications/${medicine.provider}/${medicine.externalId}`}>
      {medicine.displayName}
    </Link>
  );
}

function Metadata({ medicine }: { medicine: MedicationSummary }) {
  return (
    <p className="medicine-meta">
      {medicine.genericName && <>Generic: {medicine.genericName} · </>}
      {medicine.dosageForms.length > 0 && (
        <>{medicine.dosageForms.join(", ")} · </>
      )}
      {medicine.routes.length > 0 && <>{medicine.routes.join(", ")} · </>}
      Product label
    </p>
  );
}

export function SearchPage() {
  const [params, setParams] = useSearchParams();
  const query = params.get("q")?.trim() ?? "";
  const page = Math.max(1, Number(params.get("page")) || 1);
  const [input, setInput] = useState(query);
  const [results, setResults] = useState<Page<MedicationSummary> | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => setInput(query), [query]);
  useEffect(() => {
    if (!query) return;
    let active = true;
    setLoading(true);
    setError("");
    setResults(null);
    searchMedications(query, page)
      .then(
        (data) => {
          if (active) setResults(data);
        },
        (reason) => {
          if (active) setError(message(reason));
        },
      )
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, [query, page]);

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = input.trim();
    if (value) setParams({ q: value });
  }

  return (
    <section className="content-page" aria-labelledby="search-title">
      <p className="section-label">Explore labels</p>
      <h1 id="search-title">Medication search</h1>
      <form className="search-form" role="search" onSubmit={submit}>
        <label className="sr-only" htmlFor="medication-search">
          Medication name
        </label>
        <input
          id="medication-search"
          type="search"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          placeholder="Search a brand or generic name"
          maxLength={100}
          required
        />
        <button type="submit">Search</button>
      </form>
      <p className="page-note">
        Searches FDA product labels by brand or generic name. Similar names may
        represent different products or manufacturers.
      </p>
      {loading && <p role="status">Searching labels…</p>}
      {error && (
        <p className="page-error" role="alert">
          {error}
        </p>
      )}
      {results && (
        <>
          <p role="status">
            {results.data.length
              ? `Results for “${query}”`
              : `No labels found for “${query}”. Try another name.`}
          </p>
          <ul className="medicine-list">
            {results.data.map((medicine) => (
              <li key={medicine.externalId}>
                <MedicineLink medicine={medicine} />
                <Metadata medicine={medicine} />
                {medicine.isSaved && <span className="saved-badge">Saved</span>}
              </li>
            ))}
          </ul>
          <div className="pagination">
            {page > 1 && (
              <button
                type="button"
                onClick={() => setParams({ q: query, page: String(page - 1) })}
              >
                Previous
              </button>
            )}
            {results.pagination.hasNextPage && (
              <button
                type="button"
                onClick={() => setParams({ q: query, page: String(page + 1) })}
              >
                Next
              </button>
            )}
          </div>
        </>
      )}
    </section>
  );
}

export function DetailPage({
  account,
  onSignIn,
}: {
  account: Account | null;
  onSignIn: () => void;
}) {
  const { provider = "", externalId = "" } = useParams();
  const [medicine, setMedicine] = useState<MedicationDetail | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    setMedicine(null);
    setError("");
    medicationDetail(provider, externalId).then(
      (data) => {
        if (active) setMedicine(data);
      },
      (reason) => {
        if (active) setError(message(reason));
      },
    );
    return () => {
      active = false;
    };
  }, [provider, externalId, account]);

  async function save() {
    if (!medicine) return;
    if (!account) {
      onSignIn();
      return;
    }
    setBusy(true);
    setError("");
    try {
      await saveMedication(medicine);
      setMedicine({ ...medicine, isSaved: true });
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <article className="content-page detail-page">
      <Link className="home-link" to="/">
        ← Search another medication
      </Link>
      {error && (
        <p className="page-error" role="alert">
          {error}
        </p>
      )}
      {!medicine && !error && <p role="status">Loading label…</p>}
      {medicine && (
        <>
          <p className="section-label">FDA product label</p>
          <h1>{medicine.displayName}</h1>
          <Metadata medicine={medicine} />
          <div className="detail-actions">
            {medicine.isSaved ? (
              <span className="saved-badge">Saved to My Medication</span>
            ) : (
              <button type="button" disabled={busy} onClick={save}>
                {busy
                  ? "Saving…"
                  : account
                    ? "Save to My Medication"
                    : "Sign in to save"}
              </button>
            )}
            {medicine.isSaved && (
              <Link to="/my-medication">View My Medication</Link>
            )}
          </div>
          <p className="medical-notice">{medicine.disclaimer}</p>
          {medicine.isStale && (
            <p className="page-note">
              This is a saved copy. The latest label could not be retrieved;
              check the source for current information.
            </p>
          )}
          <dl className="label-metadata">
            <div>
              <dt>Label effective date</dt>
              <dd>{medicine.labelEffectiveDate ?? "Not provided"}</dd>
            </div>
            <div>
              <dt>Dataset updated</dt>
              <dd>{medicine.datasetUpdatedAt ?? "Not provided"}</dd>
            </div>
            <div>
              <dt>Source</dt>
              <dd>
                <a
                  href={medicine.sourceUrl}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  View on openFDA ↗
                </a>
              </dd>
            </div>
          </dl>
          {medicine.sections.length ? (
            medicine.sections.map((section) => (
              <section className="label-section" key={section.key}>
                <h2>{section.title}</h2>
                <p>{section.text}</p>
              </section>
            ))
          ) : (
            <p>No label sections are available for this product.</p>
          )}
        </>
      )}
    </article>
  );
}

export function SavedPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<Page<SavedMedication> | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);

  useEffect(() => {
    let active = true;
    setResults(null);
    setError("");
    savedMedications(page).then(
      (data) => {
        if (active) setResults(data);
      },
      (reason) => {
        if (active) setError(message(reason));
      },
    );
    return () => {
      active = false;
    };
  }, [page]);

  async function remove(item: SavedMedication) {
    setBusyId(item.savedId);
    setError("");
    try {
      await removeMedication(item.savedId);
      setConfirmId(null);
      setResults(
        (current) =>
          current && {
            ...current,
            data: current.data.filter((x) => x.savedId !== item.savedId),
          },
      );
      if (results?.data.length === 1 && page > 1) setPage(page - 1);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusyId(null);
    }
  }

  return (
    <section
      className="content-page saved-medicines"
      aria-labelledby="saved-page-title"
    >
      <p className="section-label">Your library</p>
      <h1 id="saved-page-title">My Medication</h1>
      <p className="page-note">
        Labels you save are collected here for later review.
      </p>
      {error && (
        <p className="page-error" role="alert">
          {error}
        </p>
      )}
      {!results && !error && <p role="status">Loading saved medications…</p>}
      {results &&
        (results.data.length ? (
          <>
            <ul className="medicine-list">
              {results.data.map((medicine) => (
                <li key={medicine.savedId}>
                  <MedicineLink medicine={medicine} />
                  <Metadata medicine={medicine} />
                  {medicine.isStale && (
                    <p className="page-note">
                      Saved label may be out of date. Open it to check for an
                      update.
                    </p>
                  )}
                  {confirmId === medicine.savedId ? (
                    <div className="remove-confirmation">
                      <span>Remove this label from My Medication?</span>
                      <button
                        type="button"
                        disabled={busyId === medicine.savedId}
                        onClick={() => remove(medicine)}
                      >
                        {busyId === medicine.savedId
                          ? "Removing…"
                          : "Confirm remove"}
                      </button>
                      <button
                        type="button"
                        disabled={busyId === medicine.savedId}
                        onClick={() => setConfirmId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => setConfirmId(medicine.savedId)}
                    >
                      Remove
                    </button>
                  )}
                </li>
              ))}
            </ul>
            <div className="pagination">
              {page > 1 && (
                <button type="button" onClick={() => setPage(page - 1)}>
                  Previous
                </button>
              )}
              {results.pagination.hasNextPage && (
                <button type="button" onClick={() => setPage(page + 1)}>
                  Next
                </button>
              )}
            </div>
          </>
        ) : (
          <div className="empty-state">
            <span className="empty-state-icon" aria-hidden="true">
              +
            </span>
            <h2>No saved medicines yet.</h2>
            <p>Search product labels and save ones you want to review.</p>
            <button
              type="button"
              className="home-link"
              onClick={() => navigate("/")}
            >
              Search medications
            </button>
          </div>
        ))}
      <WeeklyOrganizer />
    </section>
  );
}
