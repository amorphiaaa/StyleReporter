import { afterEach, describe, expect, it, vi } from "vitest";

import { API_BASE_URL, createManualImport, getImport } from "./client";
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
});
