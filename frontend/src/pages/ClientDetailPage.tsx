import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { createStyleReport, getClient, listStyleReports, updateClient } from "../api/client";
import type {
  ClientDetail,
  StyleReportResponse,
  StyleReportRuntimeType,
} from "../types";

type ReportsBySubmission = Record<string, StyleReportResponse[]>;

export function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>();
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [reports, setReports] = useState<ReportsBySubmission>({});
  const [selectedRuntime, setSelectedRuntime] = useState<StyleReportRuntimeType>("stub");
  const [generatingSubmissionId, setGeneratingSubmissionId] = useState<string | null>(null);
  const [isSavingClient, setIsSavingClient] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!clientId) {
      setError("Client ID is missing");
      setIsLoading(false);
      return;
    }

    setReports({});
    let isCurrent = true;
    void Promise.all([getClient(clientId), listStyleReports(clientId)])
      .then(([item, reportRuns]) => {
        if (isCurrent) {
          setClient(item);
          setReports(groupReportsBySubmission(reportRuns));
        }
      })
      .catch((requestError: unknown) => {
        if (isCurrent) {
          setError(requestError instanceof Error ? requestError.message : "Client lookup failed");
        }
      })
      .finally(() => {
        if (isCurrent) {
          setIsLoading(false);
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [clientId]);

  return (
    <section className="page">
      <Link className="back-link" to="/clients">
        ← Back to clients
      </Link>
      {isLoading ? <p className="loading-copy">Loading client profile…</p> : null}
      {error ? <p className="notice error-notice">{error}</p> : null}
      {client ? (
        <ClientProfile
          client={client}
          reports={reports}
          selectedRuntime={selectedRuntime}
          generatingSubmissionId={generatingSubmissionId}
          isSavingClient={isSavingClient}
          onRuntimeChange={setSelectedRuntime}
          onSaveDisplayName={async (displayName) => {
            setError(null);
            setIsSavingClient(true);
            try {
              const updatedClient = await updateClient(client.id, { display_name: displayName });
              setClient((current) =>
                current ? { ...current, display_name: updatedClient.display_name } : current,
              );
            } catch (requestError: unknown) {
              setError(
                requestError instanceof Error ? requestError.message : "Client update failed",
              );
            } finally {
              setIsSavingClient(false);
            }
          }}
          onGenerateReport={async (submissionId, runtime) => {
            setError(null);
            setGeneratingSubmissionId(submissionId);
            try {
              const report = await createStyleReport(client.id, {
                submission_id: submissionId,
                runtime,
              });
              setReports((current) => ({
                ...current,
                [submissionId]: [report, ...(current[submissionId] ?? [])],
              }));
            } catch (requestError: unknown) {
              setError(
                requestError instanceof Error
                  ? requestError.message
                  : "Style report generation failed",
              );
            } finally {
              setGeneratingSubmissionId(null);
            }
          }}
        />
      ) : null}
    </section>
  );
}

function ClientProfile({
  client,
  reports,
  selectedRuntime,
  generatingSubmissionId,
  isSavingClient,
  onRuntimeChange,
  onSaveDisplayName,
  onGenerateReport,
}: {
  client: ClientDetail;
  reports: ReportsBySubmission;
  selectedRuntime: StyleReportRuntimeType;
  generatingSubmissionId: string | null;
  isSavingClient: boolean;
  onRuntimeChange: (runtime: StyleReportRuntimeType) => void;
  onSaveDisplayName: (displayName: string | null) => Promise<void>;
  onGenerateReport: (submissionId: string, runtime: StyleReportRuntimeType) => Promise<void>;
}) {
  const [isEditingName, setIsEditingName] = useState(false);
  const [displayNameDraft, setDisplayNameDraft] = useState(client.display_name ?? "");

  useEffect(() => {
    setDisplayNameDraft(client.display_name ?? "");
    setIsEditingName(false);
  }, [client.id, client.display_name]);

  return (
    <>
      <div className="detail-heading">
        <div>
          <p className="eyebrow">Client profile</p>
          {!isEditingName ? <h2>{client.display_name ?? "Unnamed client"}</h2> : null}
          <p className="profile-email">{client.email_normalized}</p>
          {isEditingName ? (
            <form
              className="profile-editor"
              onSubmit={(event) => {
                event.preventDefault();
                void onSaveDisplayName(displayNameDraft.trim() || null);
              }}
            >
              <label>
                Display name
                <input
                  aria-label="Display name"
                  maxLength={255}
                  value={displayNameDraft}
                  onChange={(event) => setDisplayNameDraft(event.target.value)}
                  autoFocus
                />
              </label>
              <div className="profile-editor-actions">
                <button className="primary-button" type="submit" disabled={isSavingClient}>
                  {isSavingClient ? "Saving..." : "Save name"}
                </button>
                <button
                  className="secondary-button"
                  type="button"
                  disabled={isSavingClient}
                  onClick={() => {
                    setDisplayNameDraft(client.display_name ?? "");
                    setIsEditingName(false);
                  }}
                >
                  Cancel
                </button>
              </div>
            </form>
          ) : null}
        </div>
        <div className="detail-heading-side">
          <span className="muted-label">
            {client.submissions.length} questionnaire submission
            {client.submissions.length === 1 ? "" : "s"}
          </span>
          {!isEditingName ? (
            <button
              className="secondary-button"
              type="button"
              onClick={() => setIsEditingName(true)}
            >
              Edit profile
            </button>
          ) : null}
        </div>
      </div>

      <div className="submission-stack">
        {client.submissions.map((submission) => (
          <article className="submission-card" key={submission.id}>
            <div className="submission-heading">
              <div>
                <p className="eyebrow">Submission #{submission.source_row_number}</p>
                <h3>{submission.questionnaire_version ?? "Unversioned questionnaire"}</h3>
              </div>
              <span className="source-chip">{submission.source_type}</span>
            </div>
            <dl className="submission-meta">
              <div>
                <dt>Source sheet</dt>
                <dd>
                  {submission.sheet_name} · {submission.spreadsheet_id}
                </dd>
              </div>
              <div>
                <dt>Submitted</dt>
                <dd>{formatDate(submission.submitted_at)}</dd>
              </div>
              <div>
                <dt>Imported</dt>
                <dd>{formatDate(submission.imported_at)}</dd>
              </div>
            </dl>
            <div className="report-actions">
              <div>
                <p className="eyebrow">Methodologist runtime</p>
                <p className="report-help">
                  {selectedRuntime === "stub"
                    ? "Generate a local deterministic draft from this submission."
                    : "Construct the typed Agents SDK agent and skip the model call."}
                </p>
              </div>
              <div className="report-controls">
                <label className="runtime-select">
                  Runtime
                  <select
                    aria-label="Report runtime"
                    value={selectedRuntime}
                    onChange={(event) =>
                      onRuntimeChange(event.target.value as StyleReportRuntimeType)
                    }
                  >
                    <option value="stub">Stub report</option>
                    <option value="agents_sdk_dry_run">Agents SDK dry-run</option>
                  </select>
                </label>
                <button
                  className="primary-button"
                  type="button"
                  disabled={generatingSubmissionId === submission.id}
                  onClick={() => void onGenerateReport(submission.id, selectedRuntime)}
                >
                  {generatingSubmissionId === submission.id
                    ? "Generating..."
                    : selectedRuntime === "stub"
                      ? "Generate stub report"
                      : "Run Agents SDK dry-run"}
                </button>
              </div>
            </div>
            {reports[submission.id]?.length ? (
              <div className="report-history">
                {reports[submission.id].map((report) => (
                  <ReportPreview key={report.id} report={report} />
                ))}
              </div>
            ) : null}
            <details>
              <summary>View raw answers</summary>
              <pre className="raw-payload">{JSON.stringify(submission.raw_payload, null, 2)}</pre>
            </details>
          </article>
        ))}
      </div>
    </>
  );
}

function ReportPreview({ report }: { report: StyleReportResponse }) {
  const summary = report.report?.summary;
  return (
    <div className="report-card">
      <div className="report-heading">
        <div>
          <p className="eyebrow">Generated report</p>
          <h4>{typeof report.report?.title === "string" ? report.report.title : "Style report"}</h4>
        </div>
        <span className="success-chip">
          {report.runtime_type} · {report.report_version}
        </span>
      </div>
      <p className="report-summary">
        {typeof summary === "string" ? summary : "Report output is ready."}
      </p>
      <p className="report-meta">
        {report.status} · {formatDate(report.completed_at ?? report.created_at)}
      </p>
      <details>
        <summary>View structured report output</summary>
        <pre className="raw-payload">{JSON.stringify(report.report, null, 2)}</pre>
      </details>
    </div>
  );
}

function groupReportsBySubmission(reports: StyleReportResponse[]): ReportsBySubmission {
  return reports.reduce<ReportsBySubmission>((grouped, report) => {
    grouped[report.submission_id] = [...(grouped[report.submission_id] ?? []), report];
    return grouped;
  }, {});
}

function formatDate(value: string | null) {
  if (!value) {
    return "—";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
