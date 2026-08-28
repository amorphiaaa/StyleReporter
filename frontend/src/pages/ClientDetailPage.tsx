import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { API_BASE_URL, getClient, updateClient } from "../api/client";
import type { ClientAsset, ClientDetail } from "../types";

const PHOTO_FOLDER_ORDER = ["questionnaire", "good_outfits", "bad_outfits", "inspiration"];

export function ClientDetailPage() {
  const { clientId } = useParams<{ clientId: string }>();
  const [client, setClient] = useState<ClientDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    if (!clientId) {
      setError("Client ID is missing");
      setIsLoading(false);
      return;
    }

    let isCurrent = true;
    setIsLoading(true);
    setError(null);
    void getClient(clientId)
      .then((item) => {
        if (isCurrent) {
          setClient(item);
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
        &lt;- Back to clients
      </Link>
      {isLoading ? <p className="loading-copy">Loading client profile...</p> : null}
      {error ? <p className="notice error-notice">{error}</p> : null}
      {client ? (
        <ClientProfile
          client={client}
          onSaveDisplayName={async (displayName) => {
            setError(null);
            try {
              const updatedClient = await updateClient(client.id, { display_name: displayName });
              setClient((current) =>
                current ? { ...current, display_name: updatedClient.display_name } : current,
              );
            } catch (requestError: unknown) {
              setError(requestError instanceof Error ? requestError.message : "Client update failed");
            }
          }}
        />
      ) : null}
    </section>
  );
}

function ClientProfile({
  client,
  onSaveDisplayName,
}: {
  client: ClientDetail;
  onSaveDisplayName: (displayName: string | null) => Promise<void>;
}) {
  const [isEditingName, setIsEditingName] = useState(false);
  const [displayNameDraft, setDisplayNameDraft] = useState(client.display_name ?? "");
  const [isSavingClient, setIsSavingClient] = useState(false);

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
              onSubmit={async (event) => {
                event.preventDefault();
                setIsSavingClient(true);
                await onSaveDisplayName(displayNameDraft.trim() || null);
                setIsSavingClient(false);
                setIsEditingName(false);
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
            <button className="secondary-button" type="button" onClick={() => setIsEditingName(true)}>
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
                  {submission.sheet_name} &middot; {submission.spreadsheet_id}
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
              x
            </button>
            <img
              src={`${API_BASE_URL}${selectedAsset.url}`}
              alt={`${selectedAsset.folder_label}, image ${selectedAsset.ordinal}`}
            />
            <p>
              {selectedAsset.folder_label} &middot; {selectedAsset.filename}
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

function formatDate(value: string | null) {
  if (!value) {
    return "-";
  }
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}
