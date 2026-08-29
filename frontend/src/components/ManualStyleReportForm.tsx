import { useEffect, useMemo, useState } from "react";
import type { FormEvent } from "react";

import { API_BASE_URL, saveManualStyleReport } from "../api/client";
import type {
  ClientAsset,
  ManualReportImageGroup,
  ManualStyleReportContent,
} from "../types";

export function createEmptyManualStyleReport(): ManualStyleReportContent {
  return {
    source_text: "",
    image_groups: [],
    how_to_use: { intro: "", items: [] },
    title: "",
    alignment_summary: "",
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
}

export function ManualStyleReportForm({
  clientId,
  submissionId,
  initialContent,
  assets,
  onSaved,
}: {
  clientId: string;
  submissionId: string;
  initialContent: ManualStyleReportContent | null;
  assets: ClientAsset[];
  onSaved: (content: ManualStyleReportContent) => void;
}) {
  const [draft, setDraft] = useState(() => mergeWithEmptyContent(initialContent, assets));
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    setDraft(mergeWithEmptyContent(initialContent, assets));
    setSaveError(null);
    setSavedAt(null);
  }, [assets, initialContent]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setSaveError(null);
    try {
      const saved = await saveManualStyleReport(clientId, submissionId, draft);
      setDraft(saved.content);
      onSaved(saved.content);
      setSavedAt(new Date().toLocaleTimeString());
    } catch (requestError: unknown) {
      setSaveError(requestError instanceof Error ? requestError.message : "Manual report save failed");
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <form className="manual-report-form" onSubmit={(event) => void handleSubmit(event)}>
      <div className="manual-report-intro">
        <div>
          <p className="eyebrow">User-authored content</p>
          <h4>Signature Style Report</h4>
          <p>
            Paste the complete report in one place. The placement agent will preserve your words
            and decide which parts belong in each template field.
          </p>
        </div>
        <div className="manual-report-save-status" aria-live="polite">
          {saveError ? <span className="error-text">{saveError}</span> : null}
          {savedAt ? <span>Saved at {savedAt}</span> : null}
        </div>
      </div>

      <div className="manual-report-workspace">
        <div className="manual-report-editor-pane">
          <fieldset className="manual-report-section">
            <legend>Full report text</legend>
            <label className="manual-field">
              <span>Paste the whole report here</span>
              <textarea
                className="manual-report-source-text"
                value={draft.source_text}
                onChange={(event) =>
                  setDraft((current) => ({ ...current, source_text: event.target.value }))
                }
                placeholder="Paste the complete Signature Style Report..."
              />
            </label>
            <p className="field-help">
              Keep headings and paragraphs in the text when possible. They help the agent place
              content accurately, but no special field names are required.
            </p>
          </fieldset>

          <ImageGroupsEditor
            assets={assets}
            groups={draft.image_groups}
            onChange={(image_groups) => setDraft((current) => ({ ...current, image_groups }))}
          />

          <div className="manual-report-submit-row">
            <span>Save a draft at any point. The report remains editable.</span>
            <button className="primary-button" type="submit" disabled={isSaving}>
              {isSaving ? "Saving..." : "Save manual report"}
            </button>
          </div>
        </div>

        <ManualReportPreview draft={draft} assets={assets} />
      </div>
    </form>
  );
}

function ImageGroupsEditor({
  assets,
  groups,
  onChange,
}: {
  assets: ClientAsset[];
  groups: ManualReportImageGroup[];
  onChange: (groups: ManualReportImageGroup[]) => void;
}) {
  const assetsByKey = useMemo(
    () => new Map(assets.map((asset) => [getAssetKey(asset), asset])),
    [assets],
  );

  function updateGroup(index: number, patch: Partial<ManualReportImageGroup>) {
    onChange(groups.map((group, groupIndex) => (groupIndex === index ? { ...group, ...patch } : group)));
  }

  function toggleAsset(group: ManualReportImageGroup, asset: ClientAsset) {
    const key = getAssetKey(asset);
    const asset_keys = group.asset_keys.includes(key)
      ? group.asset_keys.filter((item) => item !== key)
      : [...group.asset_keys, key];
    return { ...group, asset_keys };
  }

  return (
    <fieldset className="manual-report-section">
      <div className="manual-list-heading">
        <legend>Image groups</legend>
        <button
          className="inline-add-button"
          type="button"
          onClick={() =>
            onChange([
              ...groups,
              {
                group_key: `custom-${groups.length + 1}`,
                label: "New image group",
                instructions: "",
                asset_keys: [],
              },
            ])
          }
        >
          Add group
        </button>
      </div>
      <p className="field-help">
        Group images by purpose, for example client portraits, outfit references, or inspiration.
        The agent will use these descriptions when choosing image slots.
      </p>
      {groups.length === 0 ? <p className="gallery-empty">No image groups yet.</p> : null}
      <div className="manual-report-image-groups">
        {groups.map((group, index) => (
          <article className="manual-report-image-group" key={group.group_key || index}>
            <div className="manual-report-image-group-heading">
              <label className="manual-field">
                <span>Group name</span>
                <input
                  value={group.label}
                  onChange={(event) => updateGroup(index, { label: event.target.value })}
                  placeholder="e.g. Client portraits"
                />
              </label>
              <button
                className="inline-remove-button"
                type="button"
                onClick={() => onChange(groups.filter((_, groupIndex) => groupIndex !== index))}
              >
                Remove
              </button>
            </div>
            <label className="manual-field">
              <span>What should these images communicate?</span>
              <textarea
                value={group.instructions}
                onChange={(event) => updateGroup(index, { instructions: event.target.value })}
                placeholder="Describe the role of this group in the report..."
              />
            </label>
            <div className="manual-report-asset-picker">
              <span className="manual-field-label">Images in this group</span>
              {assets.length === 0 ? <p className="gallery-empty">No downloaded images available.</p> : null}
              {assets.map((asset) => {
                const key = getAssetKey(asset);
                return (
                  <label className="manual-report-asset-option" key={key}>
                    <input
                      type="checkbox"
                      checked={group.asset_keys.includes(key)}
                      onChange={() => updateGroup(index, toggleAsset(group, asset))}
                    />
                    <img src={`${API_BASE_URL}${asset.url}`} alt="" loading="lazy" />
                    <span>
                      {asset.folder_label} · {asset.filename}
                    </span>
                  </label>
                );
              })}
              {group.asset_keys.some((key) => !assetsByKey.has(key)) ? (
                <p className="field-help">Some previously selected images are no longer available.</p>
              ) : null}
            </div>
          </article>
        ))}
      </div>
    </fieldset>
  );
}

function ManualReportPreview({
  draft,
  assets,
}: {
  draft: ManualStyleReportContent;
  assets: ClientAsset[];
}) {
  const assetsByKey = new Map(assets.map((asset) => [getAssetKey(asset), asset]));
  const firstLine = draft.source_text.split(/\r?\n/, 1)[0]?.trim() || "Signature Style Report";
  const paragraphs = draft.source_text
    .split(/\r?\n\s*\r?\n/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)
    .slice(0, 6);

  return (
    <aside className="manual-report-preview" aria-label="Report preview">
      <div className="manual-report-preview-heading">
        <div>
          <p className="eyebrow">Live preview</p>
          <h4>{firstLine}</h4>
        </div>
        <span className="muted-label">Draft</span>
      </div>
      <div className="manual-report-preview-copy">
        {paragraphs.length > 0 ? (
          paragraphs.map((paragraph, index) => <p key={`${paragraph.slice(0, 20)}-${index}`}>{paragraph}</p>)
        ) : (
          <p className="preview-placeholder">Your report preview will appear here as you type.</p>
        )}
      </div>
      <div className="manual-report-preview-groups">
        {draft.image_groups.map((group) => {
          const groupAssets = group.asset_keys
            .map((key) => assetsByKey.get(key))
            .filter((asset): asset is ClientAsset => Boolean(asset));
          return (
            <section className="manual-report-preview-group" key={group.group_key}>
              <h5>{group.label || "Untitled image group"}</h5>
              {group.instructions ? <p>{group.instructions}</p> : null}
              <div className="manual-report-preview-images">
                {groupAssets.map((asset) => (
                  <img
                    key={getAssetKey(asset)}
                    src={`${API_BASE_URL}${asset.url}`}
                    alt={`${group.label || "Image group"}: ${asset.filename}`}
                  />
                ))}
                {groupAssets.length === 0 ? <span>No images selected</span> : null}
              </div>
            </section>
          );
        })}
      </div>
      <p className="field-help">
        This is an editor preview. The final Canva layout is created after the placement agent
        maps the text and image groups to the template.
      </p>
    </aside>
  );
}

function mergeWithEmptyContent(
  content: ManualStyleReportContent | null,
  assets: ClientAsset[],
): ManualStyleReportContent {
  const empty = createEmptyManualStyleReport();
  const savedGroups = content?.image_groups ?? [];
  return {
    ...empty,
    ...content,
    source_text: content?.source_text ?? "",
    image_groups: savedGroups.length > 0 ? savedGroups : createDefaultImageGroups(assets),
  };
}

function createDefaultImageGroups(assets: ClientAsset[]): ManualReportImageGroup[] {
  const groups = new Map<string, ManualReportImageGroup>();
  for (const asset of assets) {
    const group = groups.get(asset.folder_key) ?? {
      group_key: asset.folder_key,
      label: asset.folder_label,
      instructions: "",
      asset_keys: [],
    };
    group.asset_keys.push(getAssetKey(asset));
    groups.set(asset.folder_key, group);
  }
  return [...groups.values()];
}

function getAssetKey(asset: ClientAsset): string {
  return `${asset.field_key}:${asset.ordinal}`;
}
