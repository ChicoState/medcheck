export type User = { id: number; username: string };
export type Session = { user: User | null; csrfToken: string };
export type Credentials = { username: string; password: string };
export type AuthErrors = Record<string, string[]>;

export class AuthError extends Error {
  constructor(
    public errors: AuthErrors,
    public status: number,
  ) {
    super("Account request failed");
  }
}

export async function requestSession(
  action: "session" | "register" | "login" | "logout",
  csrfToken?: string,
  credentials?: Credentials,
): Promise<Session> {
  const response = await fetch(`/api/auth/${action}/`, {
    method: action === "session" ? "GET" : "POST",
    credentials: "same-origin",
    cache: "no-store",
    ...(action === "session"
      ? {}
      : {
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": csrfToken ?? "",
          },
          body: JSON.stringify(credentials ?? {}),
        }),
  });
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new AuthError(
      body?.errors ?? {
        non_field_errors: [
          "Unable to complete this request. Please try again.",
        ],
      },
      response.status,
    );
  }
  return response.json();
}
