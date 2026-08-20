import { afterEach, describe, expect, it, vi } from "vitest";

import {
  API_BASE_URL,
  createManualImport,
  createStyleReport,
  getClient,
  getImport,
  getStyleReport,
  listClients,
} from "./client";
import type { ManualImportRequest } from "../types";

describe("API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("has a local development fallback", () => {
    expect(API_BASE_URL).toContain("localhost");
  });

  it("posts a manual import payload", async () => {
    const request: ManualImportRequest = {
      spreadsheet_id: "synthetic-spreadsheet",
      sheet_name: "Form Responses 1",
      email_header: "Email",
      rows: [
        {
          row_number: 2,
          values: { Email: "synthetic.client@example.test" },
        },
      ],
    };
    const responsePayload = {
      import_id: "synthetic-import",
      rows_seen: 1,
      created_clients: 1,
      updated_clients: 0,
      created_submissions: 1,
      rejected_rows: 0,
      skipped_duplicates: 0,
      errors: [],
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(responsePayload), { status: 201 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(createManualImport(request)).resolves.toEqual(responsePayload);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/imports/manual`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify(request),
      }),
    );
  });

  it("returns API detail for a failed import lookup", async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ detail: "Import was not found" }), { status: 404 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getImport("missing-import")).rejects.toThrow("Import was not found");
  });

  it("loads clients and a client detail", async () => {
    const clients = [
      {
        id: "client-1",
        email_normalized: "client@example.test",
        display_name: "Synthetic Client",
        submission_count: 1,
      },
    ];
    const detail = {
      id: "client-1",
      email_normalized: "client@example.test",
      display_name: "Synthetic Client",
      submissions: [],
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(clients), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(detail), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listClients()).resolves.toEqual(clients);
    await expect(getClient("client-1")).resolves.toEqual(detail);
    expect(fetchMock).toHaveBeenNthCalledWith(1, `${API_BASE_URL}/api/v1/clients`);
    expect(fetchMock).toHaveBeenNthCalledWith(2, `${API_BASE_URL}/api/v1/clients/client-1`);
  });

  it("generates and loads a style report", async () => {
    const report = {
      id: "report-1",
      client_id: "client-1",
      submission_id: "submission-1",
      status: "completed",
      runtime_type: "stub",
      report_version: "stub-v1",
      report: { title: "Style report draft" },
      error_message: null,
      created_at: null,
      started_at: null,
      completed_at: null,
    };
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(report), { status: 201 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(report), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      createStyleReport("client-1", { submission_id: "submission-1", runtime: "stub" }),
    ).resolves.toEqual(report);
    await expect(getStyleReport("report-1")).resolves.toEqual(report);
    expect(fetchMock).toHaveBeenNthCalledWith(
      1,
      `${API_BASE_URL}/api/v1/clients/client-1/reports`,
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ submission_id: "submission-1", runtime: "stub" }),
      }),
    );
    expect(fetchMock).toHaveBeenNthCalledWith(2, `${API_BASE_URL}/api/v1/reports/report-1`);
  });
});
