import type {
  HealthResponse,
  ClientDetail,
  ClientListItem,
  ClientUpdateResponse,
  ImportResponse,
  ImportHistoryItem,
  ImportRunResponse,
  ManualStyleReportContent,
  ManualStyleReportResponse,
  ManualImportRequest,
  UpdateClientRequest,
} from "../types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";

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

export async function listImports(limit = 20): Promise<ImportHistoryItem[]> {
  const query = new URLSearchParams({ limit: String(limit) });
  const response = await fetch(`${API_BASE_URL}/api/v1/imports?${query.toString()}`);
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Import history lookup failed"));
  }

  return response.json() as Promise<ImportHistoryItem[]>;
}

export async function listClients(search?: string): Promise<ClientListItem[]> {
  const query = search ? `?${new URLSearchParams({ search }).toString()}` : "";
  const response = await fetch(`${API_BASE_URL}/api/v1/clients${query}`);
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

export async function updateClient(
  clientId: string,
  request: UpdateClientRequest,
): Promise<ClientUpdateResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/clients/${clientId}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Client update failed"));
  }

  return response.json() as Promise<ClientUpdateResponse>;
}

export async function getManualStyleReport(
  clientId: string,
  submissionId: string,
): Promise<ManualStyleReportResponse | null> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/clients/${clientId}/submissions/${submissionId}/manual-report`,
  );
  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Manual report lookup failed"));
  }

  return response.json() as Promise<ManualStyleReportResponse | null>;
}

export async function saveManualStyleReport(
  clientId: string,
  submissionId: string,
  content: ManualStyleReportContent,
): Promise<ManualStyleReportResponse> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/clients/${clientId}/submissions/${submissionId}/manual-report`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(content),
    },
  );

  if (!response.ok) {
    throw new Error(await getErrorMessage(response, "Manual report save failed"));
  }

  return response.json() as Promise<ManualStyleReportResponse>;
}

async function getErrorMessage(response: Response, fallback: string): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    return body.detail ?? fallback;
  } catch {
    return fallback;
  }
}
