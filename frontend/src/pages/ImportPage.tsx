import { useEffect, useState, type FormEvent } from "react";

import { createManualImport, listImports } from "../api/client";
import type { ImportHistoryItem, ImportResponse, ImportRow } from "../types";

const DEFAULT_ROWS = JSON.stringify(
  [
    {
      row_number: 2,
      values: {
        Timestamp: "2026-01-15T10:30:00+00:00",
        Email: "synthetic.client@example.test",
        Name: "Synthetic Client",
        "Visual world": "B",
      },
    },
  ],
  null,
  2,
);

export function ImportPage() {
  const [spreadsheetId, setSpreadsheetId] = useState("synthetic-spreadsheet");
  const [sheetName, setSheetName] = useState("Form Responses 1");
  const [emailHeader, setEmailHeader] = useState("Email");
  const [displayNameHeader, setDisplayNameHeader] = useState("Name");
  const [questionnaireVersion, setQuestionnaireVersion] = useState("fixture-v1");
  const [rowsJson, setRowsJson] = useState(DEFAULT_ROWS);
  const [result, setResult] = useState<ImportResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [history, setHistory] = useState<ImportHistoryItem[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);

  async function refreshHistory() {
    setIsHistoryLoading(true);
    setHistoryError(null);
    try {
      setHistory(await listImports());
    } catch (requestError) {
      setHistoryError(
        requestError instanceof Error ? requestError.message : "Import history lookup failed",
      );
    } finally {
      setIsHistoryLoading(false);
    }
  }

  useEffect(() => {
    void refreshHistory();
  }, []);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setResult(null);

    let rows: ImportRow[];
    try {
      rows = parseRows(rowsJson);
    } catch (parseError) {
      setError(parseError instanceof Error ? parseError.message : "Rows JSON is invalid");
      return;
    }

    setIsSubmitting(true);
    try {
      const importResult = await createManualImport({
        spreadsheet_id: spreadsheetId.trim(),
        sheet_name: sheetName.trim(),
        email_header: emailHeader.trim(),
        display_name_header: displayNameHeader.trim() || undefined,
        questionnaire_version: questionnaireVersion.trim() || undefined,
        rows,
      });
      setResult(importResult);
      await refreshHistory();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : "Import failed");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <section className="page">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Manual source</p>
          <h2>Questionnaire imports</h2>
        </div>
        <span className="muted-label">Google adapter is intentionally deferred</span>
      </div>

      <div className="import-layout">
        <form className="form-card" onSubmit={handleSubmit}>
          <div className="form-card-heading">
            <div>
              <p className="eyebrow">Already-read rows</p>
              <h3>Run a local import</h3>
            </div>
            <span className="source-chip">POST /manual</span>
          </div>

          <p className="form-help">
            Use synthetic rows now. Later the Google Sheets adapter will provide the same row
            structure automatically.
          </p>

          <div className="field-grid">
            <label>
              Spreadsheet ID
              <input value={spreadsheetId} onChange={(event) => setSpreadsheetId(event.target.value)} />
            </label>
            <label>
              Sheet name
              <input value={sheetName} onChange={(event) => setSheetName(event.target.value)} />
            </label>
            <label>
              Email column
              <input value={emailHeader} onChange={(event) => setEmailHeader(event.target.value)} />
            </label>
            <label>
              Name column
              <input
                value={displayNameHeader}
                onChange={(event) => setDisplayNameHeader(event.target.value)}
              />
            </label>
            <label>
              Questionnaire version
              <input
                value={questionnaireVersion}
                onChange={(event) => setQuestionnaireVersion(event.target.value)}
              />
            </label>
          </div>

          <label>
            Rows JSON
            <textarea
              className="rows-editor"
              value={rowsJson}
              onChange={(event) => setRowsJson(event.target.value)}
              spellCheck={false}
            />
          </label>

          <div className="form-actions">
            <button className="primary-button" disabled={isSubmitting} type="submit">
              {isSubmitting ? "Importing…" : "Run import"}
            </button>
            <span className="muted-label">No Google credentials are used</span>
          </div>

          {error ? <p className="notice error-notice">{error}</p> : null}
        </form>

        <ImportResultCard result={result} />
      </div>
      <ImportHistory history={history} error={historyError} isLoading={isHistoryLoading} />
    </section>
  );
}

function ImportHistory({
  history,
  error,
  isLoading,
}: {
  history: ImportHistoryItem[];
  error: string | null;
  isLoading: boolean;
}) {
  return (
    <section className="history-card">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Operator view</p>
          <h3>Import history</h3>
        </div>
        <span className="muted-label">Latest 20 runs</span>
      </div>
      {isLoading ? <p className="loading-copy">Loading import historyâ€¦</p> : null}
      {error ? <p className="notice error-notice">{error}</p> : null}
      {!isLoading && !error && history.length === 0 ? (
        <p className="history-empty">No import runs have been recorded yet.</p>
      ) : null}
      {!isLoading && !error && history.length > 0 ? (
        <div className="import-history-list">
          {history.map((item) => (
            <ImportHistoryItemCard key={item.import_id} item={item} />
          ))}
        </div>
      ) : null}
    </section>
  );
}

function ImportHistoryItemCard({ item }: { item: ImportHistoryItem }) {
  return (
    <article className="import-history-item">
      <div>
        <p className="eyebrow">{item.source_type}</p>
        <h4>{item.sheet_name}</h4>
        <code className="import-history-id">{item.import_id}</code>
      </div>
      <span className={importStatusClass(item.status)}>{item.status}</span>
      <div className="import-history-metrics">
        <span>{item.rows_seen} rows</span>
        <span>{item.created_submissions} submissions</span>
        <span>{item.rejected_rows} rejected</span>
        <span>{item.row_errors_count} row errors</span>
      </div>
      <p className="import-history-date">{formatImportDate(item.completed_at ?? item.started_at)}</p>
    </article>
  );
}

function importStatusClass(status: string) {
  if (status === "completed") {
    return "status-chip status-completed";
  }
  if (status === "running") {
    return "status-chip status-running";
  }
  return "status-chip status-other";
}

function formatImportDate(value: string) {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function ImportResultCard({ result }: { result: ImportResponse | null }) {
  if (!result) {
    return (
      <aside className="result-card result-empty">
        <p className="eyebrow">Latest run</p>
        <h3>Results will appear here</h3>
        <p>Run the synthetic import to inspect created records, rejected rows, and duplicates.</p>
      </aside>
    );
  }

  return (
    <aside className="result-card">
      <div className="result-heading">
        <div>
          <p className="eyebrow">Completed import</p>
          <h3>Run summary</h3>
        </div>
        <span className="success-chip">Saved</span>
      </div>
      <code className="import-id">{result.import_id}</code>
      <div className="metric-grid">
        <Metric label="Rows" value={result.rows_seen} />
        <Metric label="Clients" value={result.created_clients} />
        <Metric label="Submissions" value={result.created_submissions} />
        <Metric label="Rejected" value={result.rejected_rows} />
        <Metric label="Duplicates" value={result.skipped_duplicates} />
      </div>
      {result.errors.length > 0 ? (
        <div className="error-list">
          <p className="eyebrow">Row errors</p>
          {result.errors.map((item) => (
            <p key={`${item.row_number}-${item.code}`}>
              Row {item.row_number}: {item.message}
            </p>
          ))}
        </div>
      ) : (
        <p className="success-copy">All submitted rows were accepted.</p>
      )}
    </aside>
  );
}

function Metric({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function parseRows(value: string): ImportRow[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(value);
  } catch {
    throw new Error("Rows must be valid JSON");
  }

  if (!Array.isArray(parsed) || parsed.length === 0) {
    throw new Error("Rows JSON must be a non-empty array");
  }

  for (const row of parsed) {
    if (
      typeof row !== "object" ||
      row === null ||
      typeof row.row_number !== "number" ||
      !Number.isInteger(row.row_number) ||
      row.row_number < 1 ||
      typeof row.values !== "object" ||
      row.values === null
    ) {
      throw new Error("Each row needs a positive integer row_number and values object");
    }
  }

  return parsed as ImportRow[];
}
