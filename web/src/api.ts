export type User = {
  id: number;
  email: string;
};

export type Medication = {
  id: number;
  name: string;
  dosage: string;
  frequency: string;
};

type ErrorResponse = {
  error?: {
    message?: string;
  };
};

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api/${path}`, {
    credentials: "same-origin",
    ...init,
  });
  const body = response.status === 204 ? null : await response.json();

  if (!response.ok) {
    const error = body as ErrorResponse;
    throw new ApiError(
      error.error?.message ?? "Something went wrong.",
      response.status,
    );
  }

  return body as T;
}

async function csrfHeaders(): Promise<HeadersInit> {
  const { csrfToken } = await request<{ csrfToken: string }>("csrf/");
  return {
    "Content-Type": "application/json",
    "X-CSRFToken": csrfToken,
  };
}

async function post<T>(path: string, payload?: object): Promise<T> {
  return request<T>(path, {
    method: "POST",
    headers: await csrfHeaders(),
    body: payload ? JSON.stringify(payload) : undefined,
  });
}

export async function currentUser(): Promise<User> {
  const { user } = await request<{ user: User }>("auth/me/");
  return user;
}

export async function register(email: string, password: string): Promise<User> {
  const { user } = await post<{ user: User }>("auth/register/", {
    email,
    password,
  });
  return user;
}

export async function signIn(email: string, password: string): Promise<User> {
  const { user } = await post<{ user: User }>("auth/login/", {
    email,
    password,
  });
  return user;
}

export function signOut(): Promise<unknown> {
  return post("auth/logout/");
}

export async function listMedications(): Promise<Medication[]> {
  const { data } = await request<{ data: Medication[] }>("medications/");
  return data;
}

export function createMedication(
  input: Omit<Medication, "id">,
): Promise<Medication> {
  return post<Medication>("medications/", input);
}
