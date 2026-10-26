export type MedicationSummary = {
  provider: string;
  externalId: string;
  displayName: string;
  genericName: string | null;
  brandNames: string[];
  activeIngredients: string[];
  dosageForms: string[];
  routes: string[];
  rxcui: string | null;
  isSaved?: boolean;
};

export type MedicationDetail = MedicationSummary & {
  sections: { key: string; title: string; text: string }[];
  labelEffectiveDate: string | null;
  datasetUpdatedAt: string | null;
  fetchedAt: string;
  isStale: boolean;
  sourceUrl: string;
  disclaimer: string;
  isSaved: boolean;
};

export type SavedMedication = MedicationSummary & {
  savedId: number;
  savedAt: string;
  labelEffectiveDate: string | null;
  isStale: boolean;
};

export type Page<T> = {
  data: T[];
  pagination: { page: number; pageSize: number; hasNextPage: boolean };
};

export class MedicationError extends Error {
  constructor(
    readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(url, { credentials: "same-origin", ...options });
  } catch {
    throw new MedicationError(
      0,
      "The medication service is unavailable. Please try again.",
    );
  }
  if (response.status === 204) return undefined as T;
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new MedicationError(
      response.status,
      "The medication service returned an invalid response.",
    );
  }
  if (!response.ok) {
    const error = (body as { error?: { message?: string } })?.error;
    throw new MedicationError(
      response.status,
      error?.message ?? "The request could not be completed.",
    );
  }
  return body as T;
}

async function csrfToken(): Promise<string> {
  const data = await request<{ csrfToken: string }>("/api/auth/csrf/");
  if (typeof data.csrfToken !== "string")
    throw new MedicationError(0, "Unable to verify your session.");
  return data.csrfToken;
}

export function searchMedications(
  query: string,
  page: number,
): Promise<Page<MedicationSummary>> {
  const params = new URLSearchParams({ q: query, page: String(page) });
  return request(`/api/medications/?${params}`);
}

export function medicationDetail(
  provider: string,
  externalId: string,
): Promise<MedicationDetail> {
  return request(
    `/api/medications/${encodeURIComponent(provider)}/${encodeURIComponent(externalId)}/`,
  );
}

export function savedMedications(page: number): Promise<Page<SavedMedication>> {
  return request(`/api/saved-medications/?page=${page}`);
}

export async function saveMedication(
  medicine: MedicationSummary,
): Promise<void> {
  const token = await csrfToken();
  await request("/api/saved-medications/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: JSON.stringify({
      provider: medicine.provider,
      externalId: medicine.externalId,
    }),
  });
}

export async function removeMedication(savedId: number): Promise<void> {
  const token = await csrfToken();
  await request(`/api/saved-medications/${savedId}/`, {
    method: "DELETE",
    headers: { "X-CSRFToken": token },
  });
}

export type ScheduledMedicine = {
  id: number;
  name: string;
  time: string;
  food: "with food" | "without food";
};

export type MedicationSchedule = Record<string, ScheduledMedicine[]>;

async function readJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    throw new Error("The medication service returned an invalid response.");
  }
}

export async function currentMedicationSchedule(): Promise<MedicationSchedule> {
  let response: Response;
  try {
    response = await fetch("/api/medications/schedule/", {
      credentials: "same-origin",
    });
  } catch {
    throw new Error(
      "The medication service is unavailable. Start Django on port 8000.",
    );
  }
  if (!response.ok) {
    throw new Error(
      response.status === 401
        ? "Sign in to view your medication schedule."
        : "Unable to load your medication schedule.",
    );
  }
  const data = (await readJson(response)) as {
    schedule?: MedicationSchedule;
  };
  if (!data.schedule || typeof data.schedule !== "object") {
    throw new Error("The medication service returned an invalid schedule.");
  }
  return data.schedule;
}
