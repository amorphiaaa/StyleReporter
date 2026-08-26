import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import {
  API_BASE_URL,
  createStyleReport,
  generateCanvaCandidates,
  getClient,
  listStyleReports,
  updateClient,
} from "../api/client";
import type {
  ClientAsset,
  ClientDetail,
  CanvaCandidatesResponse,
  StyleLanguageAction,
  StyleLanguageAnalysis,
  StyleReportResponse,
  StyleReportRuntimeType,
} from "../types";

type ReportsBySubmission = Record<string, StyleReportResponse[]>;
const PHOTO_FOLDER_ORDER = [
  "questionnaire",
  "good_outfits",
  "bad_outfits",
  "inspiration",
  "final_report",
];

export function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>();
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [reports, setReports] = useState<ReportsBySubmission>({});
  const [canvaCandidates, setCanvaCandidates] = useState<Record<string, CanvaCandidatesResponse>>({});
  const [selectedRuntime, setSelectedRuntime] = useState<StyleReportRuntimeType>("codex_cli");
  const [generatingSubmissionId, setGeneratingSubmissionId] = useState<string | null>(null);
  const [generatingCanvaReportId, setGeneratingCanvaReportId] = useState<string | null>(null);
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
    setCanvaCandidates({});
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
          canvaCandidates={canvaCandidates}
          selectedRuntime={selectedRuntime}
          generatingSubmissionId={generatingSubmissionId}
          generatingCanvaReportId={generatingCanvaReportId}
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
              try {
                const reportRuns = await listStyleReports(client.id);
                setReports(groupReportsBySubmission(reportRuns));
              } catch {
                // Keep the original generation error visible if history refresh also fails.
              }
            } finally {
              setGeneratingSubmissionId(null);
            }
          }}
          onGenerateCanvaCandidates={async (reportRunId) => {
            setError(null);
            setGeneratingCanvaReportId(reportRunId);
            try {
              const result = await generateCanvaCandidates(client.id, reportRunId);
              setCanvaCandidates((current) => ({ ...current, [reportRunId]: result }));
            } catch (requestError: unknown) {
              setError(
                requestError instanceof Error
                  ? requestError.message
                  : "Canva candidate generation failed",
              );
            } finally {
              setGeneratingCanvaReportId(null);
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
  canvaCandidates,
  selectedRuntime,
  generatingSubmissionId,
  generatingCanvaReportId,
  isSavingClient,
  onRuntimeChange,
  onSaveDisplayName,
  onGenerateReport,
  onGenerateCanvaCandidates,
}: {
  client: ClientDetail;
  reports: ReportsBySubmission;
  canvaCandidates: Record<string, CanvaCandidatesResponse>;
  selectedRuntime: StyleReportRuntimeType;
  generatingSubmissionId: string | null;
  generatingCanvaReportId: string | null;
  isSavingClient: boolean;
  onRuntimeChange: (runtime: StyleReportRuntimeType) => void;
  onSaveDisplayName: (displayName: string | null) => Promise<void>;
  onGenerateReport: (submissionId: string, runtime: StyleReportRuntimeType) => Promise<void>;
  onGenerateCanvaCandidates: (reportRunId: string) => Promise<void>;
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

      <ClientPhotoGallery assets={client.assets ?? []} />

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
                    : selectedRuntime === "codex_cli"
                      ? "Generate the report through the locally authenticated Codex CLI."
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
                    <option value="codex_cli">Codex CLI (local)</option>
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
                    : selectedRuntime === "codex_cli"
                      ? "Run Codex CLI report"
                      : "Run Agents SDK dry-run"}
                </button>
              </div>
            </div>
            {reports[submission.id]?.length ? (
              <div className="report-history">
                {reports[submission.id].map((report) => (
                  <ReportPreview
                    key={report.id}
                    report={report}
                    canvaCandidates={canvaCandidates[report.id]}
                    isGeneratingCanva={generatingCanvaReportId === report.id}
                    onGenerateCanvaCandidates={onGenerateCanvaCandidates}
                  />
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

function ClientPhotoGallery({ assets }: { assets: ClientAsset[] }) {
  const [selectedAsset, setSelectedAsset] = useState<ClientAsset | null>(null);
  const groupedAssets = assets.reduce<Record<string, ClientAsset[]>>((groups, asset) => {
    groups[asset.folder_key] = [...(groups[asset.folder_key] ?? []), asset];
    return groups;
  }, {});
  const groups = Object.entries(groupedAssets).sort(
    ([firstKey], [secondKey]) => photoFolderOrder(firstKey) - photoFolderOrder(secondKey),
  );

  useEffect(() => {
    if (!selectedAsset) {
      return;
    }

    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setSelectedAsset(null);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedAsset]);

  return (
    <section className="client-gallery" aria-labelledby="client-gallery-heading">
      <div className="gallery-heading">
        <div>
          <p className="eyebrow">Visual references</p>
          <h3 id="client-gallery-heading">Client photos</h3>
        </div>
        <span className="muted-label">
          {assets.length} saved image{assets.length === 1 ? "" : "s"}
        </span>
      </div>
      {assets.length === 0 ? (
        <p className="gallery-empty">
          No local images are available yet. They will appear here after a successful asset
          download during import.
        </p>
      ) : (
        <div className="gallery-groups">
          {groups.map(([folderKey, folderAssets]) => (
            <section className="gallery-group" key={folderKey}>
              <div className="gallery-group-heading">
                <h4>{folderAssets[0]?.folder_label ?? folderKey}</h4>
                <span>{folderAssets.length}</span>
              </div>
              <div className="photo-grid">
                {folderAssets.map((asset) => (
                  <button
                    className="photo-tile"
                    type="button"
                    key={`${asset.submission_id}-${asset.field_key}-${asset.ordinal}`}
                    onClick={() => setSelectedAsset(asset)}
                    aria-label={`Open ${asset.folder_label} image ${asset.ordinal}`}
                  >
                    <img
                      src={`${API_BASE_URL}${asset.url}`}
                      alt={`${asset.folder_label}, image ${asset.ordinal}`}
                      loading="lazy"
                    />
                    <span>{asset.filename}</span>
                  </button>
                ))}
              </div>
            </section>
          ))}
        </div>
      )}
      {selectedAsset ? (
        <div
          className="photo-lightbox"
          role="dialog"
          aria-modal="true"
          aria-label={`${selectedAsset.folder_label} image preview`}
          onClick={() => setSelectedAsset(null)}
        >
          <div className="photo-lightbox-panel" onClick={(event) => event.stopPropagation()}>
            <button
              className="photo-lightbox-close"
              type="button"
              onClick={() => setSelectedAsset(null)}
              aria-label="Close image preview"
            >
              ×
            </button>
            <img
              src={`${API_BASE_URL}${selectedAsset.url}`}
              alt={`${selectedAsset.folder_label}, image ${selectedAsset.ordinal}`}
            />
            <p>
              {selectedAsset.folder_label} · {selectedAsset.filename}
            </p>
          </div>
        </div>
      ) : null}
    </section>
  );
}

function photoFolderOrder(folderKey: string): number {
  const index = PHOTO_FOLDER_ORDER.indexOf(folderKey);
  return index === -1 ? PHOTO_FOLDER_ORDER.length : index;
}

function ReportPreview({
  report,
  canvaCandidates,
  isGeneratingCanva,
  onGenerateCanvaCandidates,
}: {
  report: StyleReportResponse;
  canvaCandidates?: CanvaCandidatesResponse;
  isGeneratingCanva: boolean;
  onGenerateCanvaCandidates: (reportRunId: string) => Promise<void>;
}) {
  const isFailed = report.status === "failed";
  const summary = report.report?.summary;
  const analysis = readStyleLanguageAnalysis(report.report);
  return (
    <div className={`report-card${isFailed ? " report-card-failed" : ""}`}>
      <div className="report-heading">
        <div>
          <p className="eyebrow">{isFailed ? "Report attempt failed" : "Generated report"}</p>
          <h4>
            {isFailed
              ? "Style report unavailable"
              : typeof report.report?.title === "string"
                ? report.report.title
                : "Style report"}
          </h4>
        </div>
        <span className={isFailed ? "error-chip" : "success-chip"}>
          {report.runtime_type} · {report.report_version}
        </span>
      </div>
      <p className={isFailed ? "report-error" : "report-summary"}>
        {isFailed
          ? report.error_message ?? "The runtime failed without additional details."
          : typeof summary === "string"
            ? summary
            : "Report output is ready."}
      </p>
      <p className="report-meta">
        {report.status} · {formatDate(report.completed_at ?? report.created_at)}
      </p>
      {!isFailed ? (
        <div className="canva-actions">
          <button
            className="secondary-button"
            type="button"
            disabled={isGeneratingCanva}
            onClick={() => void onGenerateCanvaCandidates(report.id)}
          >
            {isGeneratingCanva ? "Creating Canva candidates..." : "Generate Canva candidates"}
          </button>
          {canvaCandidates ? <CanvaCandidatesView result={canvaCandidates} /> : null}
        </div>
      ) : null}
      {analysis ? <StyleLanguageAnalysisView analysis={analysis} /> : null}
      {report.report ? (
        <details>
          <summary>View structured report output</summary>
          <pre className="raw-payload">{JSON.stringify(report.report, null, 2)}</pre>
        </details>
      ) : null}
    </div>
  );
}

function CanvaCandidatesView({ result }: { result: CanvaCandidatesResponse }) {
  return (
    <div className="canva-candidates">
      <p className="eyebrow">Canva design candidates</p>
      <p className="canva-note">{result.note}</p>
      {result.candidates.length > 0 ? (
        <div className="canva-candidate-list">
          {result.candidates.map((candidate) => (
            <a
              className="canva-candidate"
              href={candidate.design_url ?? candidate.thumbnail_url ?? undefined}
              target="_blank"
              rel="noreferrer"
              key={`${candidate.job_id}-${candidate.candidate_id}`}
            >
              {candidate.thumbnail_url ? (
                <img src={candidate.thumbnail_url} alt="" loading="lazy" />
              ) : null}
              <span>{candidate.title}</span>
            </a>
          ))}
        </div>
      ) : null}
    </div>
  );
}

function StyleLanguageAnalysisView({ analysis }: { analysis: StyleLanguageAnalysis }) {
  return (
    <div className="style-analysis">
      {analysis.alignment_summary ? (
        <p className="alignment-summary">{analysis.alignment_summary}</p>
      ) : null}
      <div className="analysis-grid">
        <StyleLanguageContrast
          current={analysis.current_style_language}
          desired={analysis.desired_style_language}
        />
        <AnalysisBlock label="The Disconnect" value={analysis.disconnect} />
      </div>
      {analysis.style_language_summary ? (
        <div className="style-language-summary">
          <div>
            <p className="eyebrow">Signature Style Language</p>
            <h5>{analysis.title}</h5>
          </div>
          <p>{analysis.style_language_summary}</p>
          {analysis.style_language_anchors.length > 0 ? (
            <p className="style-language-anchors">
              {analysis.style_language_anchors.join(" · ")}
            </p>
          ) : null}
        </div>
      ) : null}
      <div className="action-plan">
        <div className="analysis-section-heading">
          <p className="eyebrow">Client-facing next steps</p>
          <h5>Your Action Plan</h5>
        </div>
        <div className="action-plan-list">
          {analysis.your_action_plan.map((item) => (
            <article className="action-plan-item" key={`${item.priority}-${item.focus}`}>
              <span className="action-plan-number">{item.priority}</span>
              <div>
                <h6>{item.focus}</h6>
                <p>{item.action}</p>
                <small>{item.rationale}</small>
              </div>
            </article>
          ))}
        </div>
      </div>
      {analysis.limitations.length > 0 ? (
        <details className="analysis-limitations">
          <summary>Evidence and limitations</summary>
          <p className="eyebrow">Evidence</p>
          {analysis.evidence.map((item) => (
            <p key={item}>{item}</p>
          ))}
          <p className="eyebrow">Limitations</p>
          {analysis.limitations.map((item) => (
            <p key={item}>{item}</p>
          ))}
        </details>
      ) : null}
    </div>
  );
}

function StyleLanguageContrast({
  current,
  desired,
}: {
  current: string[];
  desired: string[];
}) {
  const pairCount = Math.min(current.length, desired.length);

  return (
    <article className="analysis-block style-language-contrast">
      <div className="style-language-contrast-header">
        <p className="eyebrow">Style Language movement</p>
        <div className="style-language-column-labels" aria-hidden="true">
          <span>Current</span>
          <span>Desired</span>
        </div>
      </div>
      <div className="style-language-pairs">
        {Array.from({ length: pairCount }, (_, index) => (
          <div
            className="style-language-pair"
            key={`${current[index]}-${desired[index]}-${index}`}
          >
            <span>{current[index]}</span>
            <span className="style-language-arrow" aria-hidden="true">
              →
            </span>
            <span>{desired[index]}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function AnalysisBlock({ label, value }: { label: string; value: string | string[] }) {
  const items = Array.isArray(value) ? value : null;
  return (
    <article className="analysis-block">
      <p className="eyebrow">{label}</p>
      {items ? (
        <ul className="analysis-terms">
          {items.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : (
        <p>{value}</p>
      )}
    </article>
  );
}

function readStyleLanguageAnalysis(
  report: Record<string, unknown> | null,
): StyleLanguageAnalysis | null {
  if (!report) {
    return null;
  }

  const actionPlan = Array.isArray(report.your_action_plan)
    ? report.your_action_plan.filter(isStyleLanguageAction)
    : [];
  const currentStyleLanguage = readTextList(report.current_style_language);
  const desiredStyleLanguage = readTextList(report.desired_style_language);
  if (
    typeof report.title !== "string" ||
    typeof report.disconnect !== "string" ||
    actionPlan.length === 0 ||
    currentStyleLanguage.length === 0 ||
    desiredStyleLanguage.length === 0
  ) {
    return null;
  }

  return {
    title: report.title,
    alignment_summary:
      typeof report.alignment_summary === "string" ? report.alignment_summary : "",
    current_style_language: currentStyleLanguage,
    desired_style_language: desiredStyleLanguage,
    disconnect: report.disconnect,
    style_language_summary:
      typeof report.style_language_summary === "string" ? report.style_language_summary : "",
    style_language_anchors: readTextList(report.style_language_anchors),
    your_action_plan: actionPlan,
    evidence: readStringList(report.evidence),
    limitations: readStringList(report.limitations),
  };
}

function isStyleLanguageAction(value: unknown): value is StyleLanguageAction {
  if (!value || typeof value !== "object") {
    return false;
  }
  const item = value as Record<string, unknown>;
  return (
    typeof item.priority === "number" &&
    typeof item.focus === "string" &&
    typeof item.action === "string" &&
    typeof item.rationale === "string"
  );
}

function readStringList(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function readTextList(value: unknown): string[] {
  if (typeof value === "string") {
    return value.trim() ? [value] : [];
  }
  return readStringList(value);
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
