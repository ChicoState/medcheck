export type Account = { id: number; email: string; username: string };

type ApiError = { errors?: Record<string, string | string[]> };

export class AccountError extends Error {
  constructor(readonly errors: Record<string, string>) {
    super(Object.values(errors)[0] ?? "Please try again.");
  }
}

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new Error("The server returned an invalid response.");
  }
}

export async function currentAccount(): Promise<Account | null> {
  const response = await fetch("/api/auth/me/", { credentials: "same-origin" });
  if (response.status === 401) return null;
  if (!response.ok) throw new Error("Unable to check your account.");
  const data = (await readJson(response)) as { user?: Account };
  if (!data.user || typeof data.user.email !== "string") {
    throw new Error("The server returned an invalid account.");
  }
  return data.user;
}

async function csrfToken(): Promise<string> {
  let response: Response;
  try {
    response = await fetch("/api/auth/csrf/", {
      credentials: "same-origin",
    });
  } catch {
    throw new Error(
      "The account service is unavailable. Start Django on port 8000.",
    );
  }
  if (!response.ok) {
    throw new Error(
      "The account service is unavailable. Start Django on port 8000.",
    );
  }
  const data = (await readJson(response)) as { csrfToken?: string };
  if (typeof data.csrfToken !== "string") {
    throw new Error(
      "The account service returned an invalid session response.",
    );
  }
  return data.csrfToken;
}

export async function accountAction(
  action: "register" | "login" | "logout",
  values: Record<string, string> = {},
): Promise<Account | null> {
  const token = await csrfToken();
  const response = await fetch(`/api/auth/${action}/`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: JSON.stringify(values),
  });
  const data = (await readJson(response)) as { user?: Account } & ApiError;
  if (!response.ok) {
    const errors = Object.fromEntries(
      Object.entries(data.errors ?? {}).map(([field, message]) => [
        field,
        Array.isArray(message) ? message.join(" ") : message,
      ]),
    );
    throw new AccountError(
      Object.keys(errors).length ? errors : { form: "Please try again." },
    );
  }
  if (action === "logout") return null;
  if (!data.user || typeof data.user.email !== "string") {
    throw new Error("The server returned an invalid account.");
  }
  return data.user;
}
