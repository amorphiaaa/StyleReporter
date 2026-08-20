import type {
  HealthResponse,
  ClientDetail,
  ClientListItem,
  ImportResponse,
  ImportRunResponse,
  ManualImportRequest,
} from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export async function getHealth(): Promise<HealthResponse> {
  const response = await fetch(API_BASE_URL + "/health");
  if (!response.ok) {
    throw new Error("API health check failed");
  }
  return response.json() as Promise<HealthResponse>;
}

export async function createManualImport(
  request: ManualImportRequest,
): Promise<ImportResponse> {
  const response = await fetch(API_BASE_URL + "/api/v1/imports/manual", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Manual import failed"));
  }

  return response.json() as Promise<ImportResponse>;
}

export async function getImport(importId: string): Promise<ImportRunResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/imports/${importId}`);
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Import lookup failed"));
  }

  return response.json() as Promise<ImportRunResponse>;
}

export async function listClients(): Promise<ClientListItem[]> {
  const response = await fetch(`${API_BASE_URL}/api/v1/clients`);
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Client list lookup failed"));
  }

  return response.json() as Promise<ClientListItem[]>;
}

export async function getClient(clientId: string): Promise<ClientDetail> {
  const response = await fetch(`${API_BASE_URL}/api/v1/clients/${clientId}`);
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Client lookup failed"));
  }

  return response.json() as Promise<ClientDetail>;
}

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? fallback;
  } catch {
    return fallback;
  }
}
