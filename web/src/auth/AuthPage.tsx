import { useState, type FormEvent } from "react";
import { NavLink, Navigate } from "react-router-dom";
import type { AuthErrors } from "./api";
import type { Auth } from "./useAuth";

export function SessionStatus({ auth }: { auth: Auth }) {
  return auth.sessionError ? (
    <div className="session-status" role="alert">
      <p>Unable to check your account. Please try again.</p>
      <button className="primary-button" onClick={() => void auth.restore()}>
        Try again
      </button>
    </div>
  ) : (
    <p role="status">Checking your account…</p>
  );
}

export function AuthPage({
  mode,
  auth,
}: {
  mode: "register" | "login";
  auth: Auth;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [errors, setErrors] = useState<AuthErrors>({});
  const registering = mode === "register";
  const title = registering ? "Create account" : "Sign in";

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setErrors({});
    const result = await auth.submit(mode, { username, password });
    setPassword("");
    if (result) setErrors(result);
  }

  if (auth.loading || auth.sessionError) return <SessionStatus auth={auth} />;
  if (auth.user) return <Navigate to="/" replace />;

  return (
    <section className="auth-panel" aria-labelledby="auth-title">
      <p className="section-label">MedCheck</p>
      <h1 id="auth-title">{title}</h1>
      <p>
        {registering
          ? "Get started with a username and password."
          : "Welcome back. Enter your account details."}
      </p>
      <form
        className="auth-form"
        onSubmit={(event) => void handleSubmit(event)}
        aria-busy={auth.busy}
      >
        {Object.keys(errors).length > 0 && (
          <div className="auth-errors" role="alert">
            {Object.entries(errors).flatMap(([field, messages]) =>
              messages.map((message, index) => (
                <p key={`${field}-${index}`}>{message}</p>
              )),
            )}
          </div>
        )}
        <label htmlFor="username">Username</label>
        <input
          id="username"
          name="username"
          autoComplete="username"
          required
          maxLength={150}
          value={username}
          onChange={(event) => setUsername(event.target.value)}
          aria-invalid={!!errors.username}
          disabled={auth.busy}
        />
        <label htmlFor="password">Password</label>
        <input
          id="password"
          name="password"
          type="password"
          required
          autoComplete={registering ? "new-password" : "current-password"}
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          aria-invalid={!!errors.password}
          aria-describedby={registering ? "password-help" : undefined}
          disabled={auth.busy}
        />
        {registering && (
          <p id="password-help" className="field-help">
            Use at least 8 characters. Avoid common passwords, only numbers, or
            your username.
          </p>
        )}
        <button className="primary-button" type="submit" disabled={auth.busy}>
          {auth.busy ? "Please wait…" : title}
        </button>
      </form>
      <p>
        {registering ? "Already have an account? " : "New to MedCheck? "}
        <NavLink to={registering ? "/sign-in" : "/register"}>
          {registering ? "Sign in" : "Create account"}
        </NavLink>
      </p>
      <NavLink to="/">Return Home</NavLink>
    </section>
  );
}
