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
