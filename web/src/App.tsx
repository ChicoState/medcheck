import { FormEvent, useEffect, useState } from "react";

type Profile = { email: string; date_of_birth: string | null; gender: string };
type Medication = { id: number; name: string };

async function api<T>(path: string, method = "GET", body?: object): Promise<T> {
  if (method !== "GET")
    await fetch("/api/auth/csrf/", { credentials: "same-origin" });
  const token = document.cookie
    .split("; ")
    .find((item) => item.startsWith("csrftoken="))
    ?.split("=")[1];
  const response = await fetch(path, {
    method,
    credentials: "same-origin",
    headers:
      method !== "GET"
        ? {
            ...(body ? { "Content-Type": "application/json" } : {}),
            "X-CSRFToken": token ?? "",
          }
        : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!response.ok)
    throw new Error(
      (
        (await response.json().catch(() => ({}))) as {
          error?: { message?: string };
        }
      ).error?.message ?? "Please try again.",
    );
  return response.status === 204
    ? (undefined as T)
    : ((await response.json()) as T);
}

export function App() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [meds, setMeds] = useState<Medication[]>([]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [name, setName] = useState("");
  const [mode, setMode] = useState<"register" | "login">("register");
  const [error, setError] = useState("");
  useEffect(() => {
    api<Profile>("/api/me/")
      .then((value) => {
        setProfile(value);
        return api<Medication[]>("/api/medications/");
      })
      .then(setMeds)
      .catch(() => undefined);
  }, []);
  async function account(event: FormEvent) {
    event.preventDefault();
    setError("");
    try {
      const current = await api<Profile>(`/api/auth/${mode}/`, "POST", {
        email,
        password,
      });
      setProfile(current);
      setMeds(await api<Medication[]>("/api/medications/"));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Please try again.");
    }
  }
  async function add(event: FormEvent) {
    event.preventDefault();
    try {
      const medication = await api<Medication>("/api/medications/", "POST", {
        name,
      });
      setMeds([...meds, medication]);
      setName("");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Please try again.");
    }
  }
  async function saveProfile(event: FormEvent) {
    event.preventDefault();
    if (!profile) return;
    try {
      setProfile(await api<Profile>("/api/me/", "PATCH", profile));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Please try again.");
    }
  }
  async function remove(id: number) {
    await api<void>(`/api/medications/${id}/`, "DELETE");
    setMeds(meds.filter((item) => item.id !== id));
  }
  async function signOut() {
    await api<void>("/api/auth/logout/", "POST");
    setProfile(null);
    setMeds([]);
  }
  if (!profile)
    return (
      <main className="shell">
        <section className="panel">
          <p className="eyebrow">Medcheck</p>
          <h1>
            {mode === "register"
              ? "Create your private account"
              : "Welcome back"}
          </h1>
          <form onSubmit={account}>
            <label>
              Email
              <input
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
              />
            </label>
            <label>
              Password
              <input
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
              />
            </label>
            {error && (
              <p className="error" role="alert">
                {error}
              </p>
            )}
            <button>
              {mode === "register" ? "Create account" : "Sign in"}
            </button>
          </form>
          <button
            className="link-button"
            onClick={() => setMode(mode === "register" ? "login" : "register")}
          >
            {mode === "register"
              ? "Already have an account? Sign in"
              : "Need an account? Create one"}
          </button>
        </section>
      </main>
    );
  return (
    <main className="shell">
      <header className="masthead">
        <p className="eyebrow">Medcheck</p>
        <button className="link-button" onClick={signOut}>
          Sign out
        </button>
      </header>
      <section className="intro">
        <h1>Your health workspace</h1>
        <p>{profile.email}</p>
      </section>
      <div className="workspace">
        <section className="panel">
          <h2>Your profile</h2>
          <form onSubmit={saveProfile}>
            <label>
              Date of birth
              <input
                type="date"
                value={profile.date_of_birth ?? ""}
                onChange={(event) =>
                  setProfile({
                    ...profile,
                    date_of_birth: event.target.value || null,
                  })
                }
              />
            </label>
            <label>
              Gender (optional)
              <input
                value={profile.gender}
                onChange={(event) =>
                  setProfile({ ...profile, gender: event.target.value })
                }
                maxLength={100}
              />
            </label>
            <button>Save profile</button>
          </form>
        </section>
        <section className="panel">
          <h2>Medications</h2>
          <form onSubmit={add}>
            <label>
              Medication name
              <input
                value={name}
                onChange={(event) => setName(event.target.value)}
                required
                maxLength={255}
              />
            </label>
            <button>Add medication</button>
          </form>
          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
          <ul>
            {meds.map((medication) => (
              <li key={medication.id}>
                {medication.name}
                <button
                  className="link-button"
                  onClick={() => remove(medication.id)}
                >
                  Remove
                </button>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </main>
  );
}
