import { FormEvent, useEffect, useState } from "react";
import {
  Link,
  useNavigate,
  useParams,
  useSearchParams,
} from "react-router-dom";
import { Account } from "./auth";
import capsulePill from "./assets/pill-capsule.svg";
import ovalPill from "./assets/pill-oval.svg";
import roundPill from "./assets/pill-round.svg";
import {
  MedicationDetail,
  MedicationSummary,
  InteractionResult,
  SavedInteractionStatus,
  Page,
  SavedMedication,
  MedicationSchedule,
  SchedulePlan,
  currentMedicationSchedule,
  updateMedicationSchedule,
  removeMedicationSchedule,
  medicationDetail,
  removeMedication,
  saveMedication,
  savedMedications,
  checkInteractions,
  savedInteractionStatus,
  searchMedications,
} from "./medications";

function message(error: unknown) {
  return error instanceof Error ? error.message : "Please try again.";
}

const DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];
const PERIODS = ["morning", "afternoon", "evening"] as const;
const DEFAULT_TIMES = {
  morning: "08:00",
  afternoon: "13:00",
  evening: "20:00",
};

function displayTime(value: string) {
  const [hour, minute] = value.split(":").map(Number);
  return `${hour % 12 || 12}:${String(minute).padStart(2, "0")} ${hour < 12 ? "AM" : "PM"}`;
}

function MedicineScheduleControl({
  medicine,
  onChange,
}: {
  medicine: SavedMedication;
  onChange: (plan: SchedulePlan | null) => void;
}) {
  const [plan, setPlan] = useState<SchedulePlan | null>(
    medicine.schedulePlan ?? null,
  );
  const [open, setOpen] = useState(false);
  const [days, setDays] = useState(plan?.days ?? [0, 1, 2, 3, 4]);
  const [period, setPeriod] = useState<SchedulePlan["period"]>(
    plan?.period ?? "morning",
  );
  const [time, setTime] = useState(plan?.time ?? DEFAULT_TIMES.morning);
  const [timeEdited, setTimeEdited] = useState(Boolean(plan));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  function selectPeriod(next: SchedulePlan["period"]) {
    setPeriod(next);
    if (!timeEdited) setTime(DEFAULT_TIMES[next]);
  }

  async function save(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError("");
    const next = { days: [...days].sort(), period, time };
    try {
      await updateMedicationSchedule(medicine.savedId, next);
      setPlan(next);
      setOpen(false);
      onChange(next);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(false);
    }
  }

  async function clear() {
    setBusy(true);
    setError("");
    try {
      await removeMedicationSchedule(medicine.savedId);
      setPlan(null);
      setOpen(false);
      onChange(null);
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="schedule-control">
      <div className="schedule-control-summary">
        {plan ? (
          <p>
            <span className="schedule-dot" aria-hidden="true" />
            {plan.days.map((day) => DAYS[day]).join(" · ")} · {plan.period} ·{" "}
            {displayTime(plan.time)}
          </p>
        ) : (
          <p className="schedule-unscheduled">Not in your pill case yet</p>
        )}
        <button
          type="button"
          className="schedule-toggle"
          aria-expanded={open}
          onClick={() => setOpen(!open)}
        >
          {plan ? "Edit schedule" : "Schedule"}
        </button>
      </div>
      {open && (
        <form className="schedule-form" onSubmit={save}>
          <div className="schedule-form-heading">
            <strong>Choose your days</strong>
            <div className="schedule-day-shortcuts">
              <button type="button" onClick={() => setDays([0, 1, 2, 3, 4])}>
                Every weekday
              </button>
              <button
                type="button"
                onClick={() => setDays([0, 1, 2, 3, 4, 5, 6])}
              >
                Every day
              </button>
            </div>
          </div>
          <div
            className="schedule-day-options"
            role="group"
            aria-label={`Days for ${medicine.displayName}`}
          >
            {DAYS.map((name, day) => (
              <button
                type="button"
                key={name}
                className={days.includes(day) ? "selected" : ""}
                aria-pressed={days.includes(day)}
                onClick={() =>
                  setDays((current) =>
                    current.includes(day)
                      ? current.filter((value) => value !== day)
                      : [...current, day],
                  )
                }
              >
                {name}
              </button>
            ))}
          </div>
          <strong>Time of day</strong>
          <div
            className="schedule-period-options"
            role="group"
            aria-label={`Time of day for ${medicine.displayName}`}
          >
            {PERIODS.map((option) => (
              <button
                type="button"
                key={option}
                className={period === option ? "selected" : ""}
                aria-pressed={period === option}
                onClick={() => selectPeriod(option)}
              >
                {option}
              </button>
            ))}
          </div>
          <label className="schedule-time-label">
            Exact time
            <input
              type="time"
              value={time}
              required
              onChange={(event) => {
                setTime(event.target.value);
                setTimeEdited(true);
              }}
            />
          </label>
          {error && (
            <p className="page-error" role="alert">
              {error}
            </p>
          )}
          <div className="schedule-form-actions">
            <button type="submit" disabled={busy || days.length === 0}>
              {busy ? "Saving…" : plan ? "Save changes" : "Add to pill case"}
            </button>
            {plan && (
              <button type="button" disabled={busy} onClick={clear}>
                Remove schedule
              </button>
            )}
            <button
              type="button"
              disabled={busy}
              onClick={() => setOpen(false)}
            >
              Cancel
            </button>
          </div>
        </form>
      )}
    </div>
  );
}

function WeeklyOrganizer() {
  const [selectedDay, setSelectedDay] = useState("Monday");
  const [schedule, setSchedule] = useState<MedicationSchedule | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const pillArtwork = [capsulePill, roundPill, ovalPill];
  const monday = new Date();
  const weekday = monday.getDay();
  monday.setDate(monday.getDate() - (weekday === 0 ? 6 : weekday - 1));
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date(monday);
    date.setDate(monday.getDate() + index);
    return {
      name: date.toLocaleDateString("en-US", { weekday: "long" }),
      number: date.getDate(),
    };
  });

  useEffect(() => {
    let active = true;
    currentMedicationSchedule()
      .then(
        (value) => {
          if (active) setSchedule(value);
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
  }, []);

  return (
    <section className="weekly-organizer" aria-labelledby="organizer-title">
      <div className="organizer-heading">
        <div>
          <p className="section-label">Your week at a glance</p>
          <h2 id="organizer-title">Weekly organizer</h2>
        </div>
        <p className="organizer-caption">Choose a day to view its schedule</p>
      </div>
      {loading && <p role="status">Loading medication schedule…</p>}
      {error && (
        <p className="page-error" role="alert">
          {error}
        </p>
      )}
      {!loading && !error && (
        <>
          <p className="organizer-scroll-hint">Swipe to see all seven days</p>
          <div className="organizer-scroll">
            <div
              className="organizer"
              role="group"
              aria-label="Medication week"
            >
              {days.map((day) => {
                const doses = schedule?.[day.name] ?? [];
                return (
                  <button
                    className="organizer-day"
                    type="button"
                    key={day.name}
                    aria-label={`${day.name} ${day.number}, ${doses.length} doses`}
                    aria-pressed={selectedDay === day.name}
                    onClick={() => setSelectedDay(day.name)}
                  >
                    <span className="compartment-lid">
                      <span className="compartment-weekday">
                        {day.name.slice(0, 3)}
                      </span>
                      <span className="compartment-date">{day.number}</span>
                    </span>
                    <span className="compartment-well" aria-hidden="true">
                      {doses.slice(0, 3).map((dose, index) => (
                        <img
                          className={`pill-art pill-art-${index + 1}`}
                          src={pillArtwork[index % pillArtwork.length]}
                          alt=""
                          key={dose.id}
                        />
                      ))}
                      {doses.length > 3 && (
                        <span className="compartment-more">
                          +{doses.length - 3}
                        </span>
                      )}
                    </span>
                    <span className="compartment-latch" aria-hidden="true" />
                  </button>
                );
              })}
            </div>
          </div>
          <div className="organizer-details" aria-live="polite">
            <div className="organizer-details-heading">
              <span className="organizer-details-mark" aria-hidden="true" />
              <div>
                <p className="section-label">Open compartment</p>
                <h3>{selectedDay}&apos;s medicines</h3>
              </div>
            </div>
            {(schedule?.[selectedDay] ?? []).length ? (
              <ul className="dose-list">
                {schedule?.[selectedDay]?.map((dose, index) => (
                  <li key={dose.id}>
                    <img
                      className="dose-art"
                      src={pillArtwork[index % pillArtwork.length]}
                      alt=""
                    />
                    <strong>{dose.name}</strong>
                    <span className="dose-time">
                      {dose.period ? `${dose.period} · ` : ""}
                      {dose.time}
                    </span>
                    {dose.food && (
                      <span className="dose-food">
                        {dose.food === "with food"
                          ? "Take with food"
                          : "Take without food"}
                      </span>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p>No medicines scheduled for this day.</p>
            )}
          </div>
        </>
      )}
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
            <Link
              to={`/interactions?firstProvider=${encodeURIComponent(
                medicine.provider,
              )}&firstId=${encodeURIComponent(medicine.externalId)}`}
            >
              Check against another medication
            </Link>
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

export function InteractionPage() {
  const [params] = useSearchParams();
  const firstProvider = params.get("firstProvider") ?? "";
  const firstId = params.get("firstId") ?? "";
  const [first, setFirst] = useState<MedicationDetail | null>(null);
  const [secondQuery, setSecondQuery] = useState("");
  const [matches, setMatches] = useState<Page<MedicationSummary> | null>(null);
  const [second, setSecond] = useState<MedicationSummary | null>(null);
  const [result, setResult] = useState<InteractionResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!firstProvider || !firstId) return;
    medicationDetail(firstProvider, firstId).then(setFirst, (reason) =>
      setError(message(reason)),
    );
  }, [firstProvider, firstId]);

  async function findSecond(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const query = secondQuery.trim();
    if (!query) return;
    setBusy(true);
    setError("");
    setMatches(null);
    setSecond(null);
    setResult(null);
    try {
      setMatches(await searchMedications(query, 1));
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(false);
    }
  }

  async function runCheck() {
    if (!first || !second) return;
    setBusy(true);
    setError("");
    try {
      setResult(await checkInteractions(first, second));
    } catch (reason) {
      setError(message(reason));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="content-page" aria-labelledby="interaction-title">
      <p className="section-label">Label screening</p>
      <h1 id="interaction-title">Check two medications</h1>
      <p className="page-note">
        Select exact product labels. We check whether either label names the
        other product or ingredient in its drug-interactions section.
      </p>
      {error && (
        <p className="page-error" role="alert">
          {error}
        </p>
      )}
      {!first && !error && <p role="status">Loading first medication…</p>}
      {first && (
        <div className="interaction-card">
          <h2>First medication</h2>
          <p>
            <strong>{first.displayName}</strong>
            {first.genericName && <> · {first.genericName}</>}
          </p>
        </div>
      )}
      <form className="search-form interaction-search" onSubmit={findSecond}>
        <label className="sr-only" htmlFor="second-medication">
          Search for the second medication
        </label>
        <input
          id="second-medication"
          type="search"
          value={secondQuery}
          onChange={(event) => setSecondQuery(event.target.value)}
          placeholder="Search the second brand or generic name"
          maxLength={100}
          required
        />
        <button type="submit" disabled={busy}>
          Find
        </button>
      </form>
      {matches && (
        <ul className="medicine-list" aria-label="Second medication choices">
          {matches.data.map((medicine) => (
            <li key={medicine.externalId}>
              <MedicineLink medicine={medicine} />
              <Metadata medicine={medicine} />
              <button
                type="button"
                disabled={medicine.externalId === first?.externalId}
                onClick={() => {
                  setSecond(medicine);
                  setResult(null);
                  setError("");
                }}
              >
                {medicine.externalId === first?.externalId
                  ? "Already selected"
                  : second?.externalId === medicine.externalId
                    ? "Selected"
                    : "Select"}
              </button>
            </li>
          ))}
        </ul>
      )}
      {second && (
        <div className="interaction-card">
          <h2>Second medication</h2>
          <p>
            <strong>{second.displayName}</strong>
            {second.genericName && <> · {second.genericName}</>}
          </p>
          <button type="button" disabled={busy} onClick={runCheck}>
            {busy ? "Checking…" : "Check labels"}
          </button>
        </div>
      )}
      {result && <InteractionResults result={result} />}
    </section>
  );
}

function InteractionResults({ result }: { result: InteractionResult }) {
  return (
    <section className="interaction-result" aria-live="polite">
      <h2>
        {result.status === "label_match"
          ? "Interaction information found"
          : "No matching interaction text found"}
      </h2>
      {result.status === "label_match" ? (
        result.findings.map((finding) => (
          <article
            className="interaction-finding"
            key={finding.sourceMedication}
          >
            <h3>{finding.sourceMedication} label</h3>
            <p>{finding.text}</p>
            <p className="page-note">
              Matched: {finding.matchedTerm}. Label effective:{" "}
              {finding.labelEffectiveDate ?? "not provided"}. Dataset updated:{" "}
              {finding.datasetUpdatedAt ?? "not provided"}.{" "}
              <a
                href={finding.sourceUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                View source ↗
              </a>
            </p>
          </article>
        ))
      ) : (
        <p>
          Neither retrieved label named the other selected product or ingredient
          in its interaction section.
        </p>
      )}
      <p className="medical-notice">{result.disclaimer}</p>
    </section>
  );
}

function LibraryInteractionStatus() {
  const [result, setResult] = useState<SavedInteractionStatus | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    savedInteractionStatus().then(
      (value) => {
        if (active) setResult(value);
      },
      (reason) => {
        if (active) setError(message(reason));
      },
    );
    return () => {
      active = false;
    };
  }, []);

  const status = result?.status ?? "incomplete";
  const copy = !result
    ? "Checking saved product labels…"
    : status === "match"
      ? `Potential interaction information found in ${result.matches.length} ${result.matches.length === 1 ? "pair" : "pairs"}.`
      : status === "clear"
        ? `No interaction text found in ${result.pairsChecked} checked ${result.pairsChecked === 1 ? "pair" : "pairs"}.`
        : result.reason === "need_two"
          ? "Add another medicine to check pairs."
          : result.reason === "too_many"
            ? "Too many saved medicines to check at once."
            : "Unable to complete the check for every pair.";

  return (
    <section
      className={`library-interactions library-interactions-${status}`}
      aria-labelledby="library-interactions-title"
    >
      <div className="library-interactions-top">
        <span className="library-interactions-icon" aria-hidden="true">
          {error
            ? "⚪"
            : status === "match"
              ? "🔴"
              : status === "clear"
                ? "🟢"
                : "⚪"}
        </span>
        <div>
          <h2 id="library-interactions-title">Label interaction check</h2>
          {error ? (
            <p role="alert">Unable to check saved product labels. {error}</p>
          ) : (
            <p role={result ? undefined : "status"}>{copy}</p>
          )}
        </div>
      </div>
      {result && result.totalPairs > 0 && (
        <p className="library-interactions-count">
          {result.pairsChecked} of {result.totalPairs} pairs checked
        </p>
      )}
      {result?.status === "match" && (
        <details className="library-interactions-details">
          <summary>Review matches</summary>
          {result.matches.map((pair) => (
            <article key={pair.names.join(":")}>
              <h3>{pair.names.join(" + ")}</h3>
              {pair.findings.map((finding) => (
                <div
                  key={`${finding.sourceMedication}:${finding.targetMedication}`}
                >
                  <p>
                    {finding.sourceMedication} label mentions{" "}
                    {finding.matchedTerm}:
                  </p>
                  <p className="library-interactions-excerpt">{finding.text}</p>
                  <p className="library-interactions-source">
                    Label effective{" "}
                    {finding.labelEffectiveDate ?? "date unavailable"} · Dataset
                    updated {finding.datasetUpdatedAt ?? "date unavailable"} ·{" "}
                    <a
                      href={finding.sourceUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      View source ↗
                    </a>
                  </p>
                </div>
              ))}
            </article>
          ))}
        </details>
      )}
      {result?.status === "match" &&
        result.pairsChecked < result.totalPairs && (
          <p className="library-interactions-caveat">
            Some pairs could not be checked.
          </p>
        )}
      <p className="library-interactions-caveat">
        A label search cannot establish that medicines are safe together. Ask a
        pharmacist or healthcare professional.
      </p>
    </section>
  );
}

export function SavedPage() {
  const navigate = useNavigate();
  const [page, setPage] = useState(1);
  const [results, setResults] = useState<Page<SavedMedication> | null>(null);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState<number | null>(null);
  const [confirmId, setConfirmId] = useState<number | null>(null);
  const [scheduleRevision, setScheduleRevision] = useState(0);
  useEffect(() => {
    let active = true;
    setResults(null);
    setError("");
    async function loadLibrary() {
      const first = await savedMedications(1);
      const data = [...first.data];
      let current = first;
      while (active && current.pagination.hasNextPage) {
        current = await savedMedications(current.pagination.page + 1);
        data.push(...current.data);
      }
      if (active) setResults({ ...first, data });
    }
    loadLibrary().catch((reason) => {
      if (active) setError(message(reason));
    });
    return () => {
      active = false;
    };
  }, []);

  async function remove(item: SavedMedication) {
    setBusyId(item.savedId);
    setError("");
    try {
      await removeMedication(item.savedId);
      setScheduleRevision((current) => current + 1);
      setConfirmId(null);
      setResults(
        (current) =>
          current && {
            ...current,
            data: current.data.filter((x) => x.savedId !== item.savedId),
          },
      );
      if (
        results &&
        (page - 1) * results.pagination.pageSize >= results.data.length - 1 &&
        page > 1
      )
        setPage(page - 1);
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
              {results.data
                .slice(
                  (page - 1) * results.pagination.pageSize,
                  page * results.pagination.pageSize,
                )
                .map((medicine) => (
                  <li key={medicine.savedId}>
                    <MedicineLink medicine={medicine} />
                    <Metadata medicine={medicine} />
                    <MedicineScheduleControl
                      medicine={medicine}
                      onChange={() =>
                        setScheduleRevision((current) => current + 1)
                      }
                    />
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
              {page * results.pagination.pageSize < results.data.length && (
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
      {results && (
        <LibraryInteractionStatus
          key={results.data.map((item) => item.savedId).join(",")}
        />
      )}
      <WeeklyOrganizer key={scheduleRevision} />
    </section>
  );
}
