import { afterEach, describe, expect, it, vi } from "vitest";

import {
  API_BASE_URL,
  createManualImport,
  getCanvaOAuthStartUrl,
  getClient,
  getImport,
  getManualStyleReport,
  listImports,
  listClients,
  saveManualStyleReport,
  updateClient,
} from "./client";
import type { ManualImportRequest } from "../types";

describe("API client", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("has a local development fallback", () => {
    expect(API_BASE_URL).toContain("127.0.0.1");
  });

  it("builds the Canva OAuth start URL", () => {
    expect(getCanvaOAuthStartUrl()).toBe(`${API_BASE_URL}/api/v1/canva/oauth/start`);
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

  it("loads a detailed import run", async () => {
    const detail = {
      import_id: "import-1",
      source_type: "google_sheets",
      spreadsheet_id: "synthetic-spreadsheet",
      sheet_name: "Form Responses 1",
      status: "completed",
      rows_seen: 4,
      created_clients: 2,
      updated_clients: 1,
      created_submissions: 3,
      rejected_rows: 1,
      skipped_duplicates: 0,
      row_errors: [{ row_number: 4, code: "invalid_email", message: "Invalid email" }],
      started_at: "2026-08-20T18:00:00Z",
      completed_at: "2026-08-20T18:00:01Z",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(detail), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(getImport("import-1")).resolves.toEqual(detail);
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/imports/import-1`);
  });

  it("loads recent import history with a limit", async () => {
    const history = [
      {
        import_id: "import-1",
        source_type: "google_sheets",
        spreadsheet_id: "synthetic-spreadsheet",
        sheet_name: "Form Responses 1",
        status: "completed",
        rows_seen: 4,
        created_clients: 2,
        updated_clients: 1,
        created_submissions: 3,
        rejected_rows: 1,
        skipped_duplicates: 0,
        row_errors_count: 1,
        started_at: "2026-08-20T18:00:00Z",
        completed_at: "2026-08-20T18:00:01Z",
      },
    ];
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(history), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(listImports(5)).resolves.toEqual(history);
    expect(fetchMock).toHaveBeenCalledWith(`${API_BASE_URL}/api/v1/imports?limit=5`);
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

  it("passes a client search query", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("[]", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(listClients("Synthetic Client")).resolves.toEqual([]);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/clients?search=Synthetic+Client`,
    );
  });

  it("updates a client display name", async () => {
    const updatedClient = {
      id: "client-1",
      email_normalized: "client@example.test",
      display_name: "Updated Client",
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(updatedClient), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      updateClient("client-1", { display_name: "Updated Client" }),
    ).resolves.toEqual(updatedClient);
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/clients/client-1`,
      expect.objectContaining({
        method: "PATCH",
        body: JSON.stringify({ display_name: "Updated Client" }),
      }),
    );
  });

  it("loads an empty manual report draft", async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response("null", { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(getManualStyleReport("client-1", "submission-1")).resolves.toBeNull();
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/clients/client-1/submissions/submission-1/manual-report`,
    );
  });

  it("saves a manual report draft", async () => {
    const content = {
      source_text: "A complete manually authored report.",
      content_blocks: [],
      image_groups: [],
      how_to_use: { intro: "Use this as a guide.", items: [] },
      title: "Feminine Creative",
      alignment_summary: "A manual summary.",
      current_style_language: [],
      desired_style_language: [],
      disconnect: "",
      style_language_summary: "",
      style_language_anchors: [],
      color_palette: {},
      prints_and_textures: { intro: "", what_works: [], how_to_use: [] },
      silhouettes: { intro: "", outer_layers: [], bottoms: [], tops_and_knitwear: [], dresses: [] },
      accessories: { intro: "", core_elements: [], use_principles: [], categories: [] },
      outfit_formulas: [],
      style_anchors: [],
      what_can_distract: { intro: "", colors: [], prints: [], silhouettes: [] },
      brands: [],
      moodboard: [],
      action_plan: [],
    };
    const saved = {
      id: "manual-report-1",
      client_id: "client-1",
      submission_id: "submission-1",
      content,
      created_at: null,
      updated_at: null,
    };
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(JSON.stringify(saved), { status: 200 }),
    );
    vi.stubGlobal("fetch", fetchMock);

    await expect(saveManualStyleReport("client-1", "submission-1", content)).resolves.toEqual(
      saved,
    );
    expect(fetchMock).toHaveBeenCalledWith(
      `${API_BASE_URL}/api/v1/clients/client-1/submissions/submission-1/manual-report`,
      expect.objectContaining({ method: "PUT", body: JSON.stringify(content) }),
    );
  });

});
