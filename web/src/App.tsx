import { FormEvent, useEffect, useState } from "react";

import {
  ApiError,
  createMedication,
  currentUser,
  listMedications,
  Medication,
  register,
  signIn,
  signOut,
  User,
} from "./api";

type AccountMode = "sign-in" | "register";

const EMPTY_MEDICATION = { name: "", dosage: "", frequency: "" };

export function App() {
  const [user, setUser] = useState<User | null>(null);
  const [medications, setMedications] = useState<Medication[]>([]);
  const [mode, setMode] = useState<AccountMode>("sign-in");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [medication, setMedication] = useState(EMPTY_MEDICATION);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    void restoreSession();
  }, []);

  async function restoreSession() {
    try {
      const signedInUser = await currentUser();
      setUser(signedInUser);
      setMedications(await listMedications());
    } catch (caught) {
      if (!(caught instanceof ApiError) || caught.status !== 401) {
        setError("We could not load your account. Try refreshing the page.");
      }
    }
  }

  async function handleAccountSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    setIsSubmitting(true);

    try {
      const signedInUser =
        mode === "register"
          ? await register(email, password)
          : await signIn(email, password);
      setUser(signedInUser);
      setPassword("");
      setMedications(await listMedications());
      setNotice(
        mode === "register" ? "Your account is ready." : "Welcome back.",
      );
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Unable to sign in.");
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleMedicationSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setNotice("");
    setIsSubmitting(true);

    try {
      const saved = await createMedication(medication);
      setMedications((current) => [saved, ...current]);
      setMedication(EMPTY_MEDICATION);
      setNotice(`${saved.name} was saved to your account.`);
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to save medication.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  async function handleSignOut() {
    setError("");
    setNotice("");
    try {
      await signOut();
      setUser(null);
      setMedications([]);
      setNotice("You are signed out. Your medications remain saved.");
    } catch (caught) {
      setError(
        caught instanceof Error ? caught.message : "Unable to sign out.",
      );
    }
  }

  return (
    <main className="shell">
      <header className="masthead">
        <p className="eyebrow">Personal medication workspace</p>
        {user ? <button onClick={handleSignOut}>Sign out</button> : null}
      </header>

      <section className="intro" aria-labelledby="page-title">
        <p className="kicker">Medcheck</p>
        <h1 id="page-title">Keep your medication list close at hand.</h1>
        <p className="summary">
          Save the medication name, dosage, and frequency to your private
          account.
        </p>
      </section>

      {error ? (
        <p className="message error" role="alert">
          {error}
        </p>
      ) : null}
      {notice ? (
        <p className="message" role="status">
          {notice}
        </p>
      ) : null}

      {user ? (
        <section className="workspace" aria-labelledby="medications-title">
          <div className="section-heading">
            <div>
              <p className="card-label">Signed in as {user.email}</p>
              <h2 id="medications-title">Your medications</h2>
            </div>
          </div>
          <form className="medication-form" onSubmit={handleMedicationSubmit}>
            <label>
              Medication name
              <input
                required
                value={medication.name}
                onChange={(event) =>
                  setMedication({ ...medication, name: event.target.value })
                }
              />
            </label>
            <label>
              Dosage
              <input
                required
                placeholder="e.g. 10 mg"
                value={medication.dosage}
                onChange={(event) =>
                  setMedication({ ...medication, dosage: event.target.value })
                }
              />
            </label>
            <label>
              Frequency
              <input
                required
                placeholder="e.g. Once daily"
                value={medication.frequency}
                onChange={(event) =>
                  setMedication({
                    ...medication,
                    frequency: event.target.value,
                  })
                }
              />
            </label>
            <button disabled={isSubmitting} type="submit">
              {isSubmitting ? "Saving…" : "Save medication"}
            </button>
          </form>
          {medications.length === 0 ? (
            <p className="empty" role="status">
              No medications saved yet.
            </p>
          ) : (
            <ul className="medication-list">
              {medications.map((item) => (
                <li key={item.id}>
                  <strong>{item.name}</strong>
                  <span>{item.dosage}</span>
                  <span>{item.frequency}</span>
                </li>
              ))}
            </ul>
          )}
        </section>
      ) : (
        <section className="account-card" aria-labelledby="account-title">
          <p className="card-label">Your account</p>
          <h2 id="account-title">
            {mode === "register" ? "Create an account" : "Sign in"}
          </h2>
          <form onSubmit={handleAccountSubmit}>
            <label>
              Email address
              <input
                autoComplete="email"
                required
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
              />
            </label>
            <label>
              Password
              <input
                autoComplete={
                  mode === "register" ? "new-password" : "current-password"
                }
                minLength={8}
                required
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
              />
            </label>
            <button disabled={isSubmitting} type="submit">
              {isSubmitting
                ? "Please wait…"
                : mode === "register"
                  ? "Create account"
                  : "Sign in"}
            </button>
          </form>
          <button
            className="text-button"
            onClick={() =>
              setMode(mode === "register" ? "sign-in" : "register")
            }
            type="button"
          >
            {mode === "register"
              ? "Already have an account? Sign in"
              : "New here? Create an account"}
          </button>
        </section>
      )}
    </main>
  );
}
