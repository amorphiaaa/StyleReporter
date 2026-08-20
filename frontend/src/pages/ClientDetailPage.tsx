import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { createStyleReport, getClient, listStyleReports } from "../api/client";
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
          onRuntimeChange={setSelectedRuntime}
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
  onRuntimeChange,
  onGenerateReport,
}: {
  client: ClientDetail;
  reports: ReportsBySubmission;
  selectedRuntime: StyleReportRuntimeType;
  generatingSubmissionId: string | null;
  onRuntimeChange: (runtime: StyleReportRuntimeType) => void;
  onGenerateReport: (submissionId: string, runtime: StyleReportRuntimeType) => Promise<void>;
}) {
  return (
    <>
      <div className="detail-heading">
        <div>
          <p className="eyebrow">Client profile</p>
          <h2>{client.display_name ?? "Unnamed client"}</h2>
          <p className="profile-email">{client.email_normalized}</p>
        </div>
        <span className="muted-label">
          {client.submissions.length} questionnaire submission
          {client.submissions.length === 1 ? "" : "s"}
        </span>
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
