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

export type InteractionFinding = {
  sourceMedication: string;
  targetMedication: string;
  matchedTerm: string;
  text: string;
  sourceUrl: string;
  labelEffectiveDate: string | null;
  datasetUpdatedAt: string | null;
};

export type InteractionResult = {
  status: "label_match" | "no_label_match";
  medications: MedicationSummary[];
  findings: InteractionFinding[];
  disclaimer: string;
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

export async function checkInteractions(
  first: MedicationSummary,
  second: MedicationSummary,
): Promise<InteractionResult> {
  const token = await csrfToken();
  return request("/api/medications/interactions/check/", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": token },
    body: JSON.stringify({
      medications: [
        { provider: first.provider, externalId: first.externalId },
        { provider: second.provider, externalId: second.externalId },
      ],
    }),
  });
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
