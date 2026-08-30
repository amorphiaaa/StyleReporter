import { useEffect, useState } from "react";
import type { FormEvent } from "react";

import {
  API_BASE_URL,
  saveManualStyleReport,
  uploadManualReportImage,
} from "../api/client";
import type {
  ManualReportImage,
  ManualReportImageGroup,
  ManualReportTextBlock,
  ManualStyleReportContent,
} from "../types";

const DEFAULT_CONTENT_BLOCKS: ManualReportTextBlock[] = [
  { block_key: "style-direction", title: "Style direction and personal positioning", text: "" },
  { block_key: "report-guide", title: "How to use this report", text: "" },
  { block_key: "style-language", title: "Style language", text: "" },
  { block_key: "colour-palette", title: "Colour palette", text: "" },
  { block_key: "prints-textures", title: "Prints and textures", text: "" },
  { block_key: "silhouettes", title: "Silhouettes and shapes", text: "" },
  { block_key: "accessories", title: "Accessories and styling", text: "" },
  { block_key: "outfit-formulas", title: "Outfit formulas", text: "" },
  { block_key: "style-anchors", title: "Style anchors", text: "" },
  { block_key: "what-to-avoid", title: "What can distract from the style", text: "" },
  { block_key: "brands-inspiration", title: "Brands and inspiration", text: "" },
  { block_key: "action-plan", title: "Action plan", text: "" },
];

export function createEmptyManualStyleReport(): ManualStyleReportContent {
  return {
    source_text: "",
    content_blocks: DEFAULT_CONTENT_BLOCKS.map((block) => ({ ...block })),
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
  onSaved,
}: {
  clientId: string;
  submissionId: string;
  initialContent: ManualStyleReportContent | null;
  onSaved: (content: ManualStyleReportContent) => void;
}) {
  const [draft, setDraft] = useState(() => mergeWithEmptyContent(initialContent));
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedAt, setSavedAt] = useState<string | null>(null);

  useEffect(() => {
    setDraft(mergeWithEmptyContent(initialContent));
    setSaveError(null);
    setSavedAt(null);
  }, [initialContent]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setIsSaving(true);
    setSaveError(null);
    try {
      const source_text = draft.content_blocks
        .filter((block) => block.text.trim())
        .map((block) => `${block.title}\n${block.text}`)
        .join("\n\n");
      const saved = await saveManualStyleReport(clientId, submissionId, { ...draft, source_text });
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
          <ContentBlocksEditor
            blocks={draft.content_blocks}
            onChange={(content_blocks) => setDraft((current) => ({ ...current, content_blocks }))}
          />

          <ImageGroupsEditor
            clientId={clientId}
            submissionId={submissionId}
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

        <ManualReportPreview draft={draft} />
      </div>
    </form>
  );
}

function ContentBlocksEditor({
  blocks,
  onChange,
}: {
  blocks: ManualReportTextBlock[];
  onChange: (blocks: ManualReportTextBlock[]) => void;
}) {
  function updateBlock(index: number, patch: Partial<ManualReportTextBlock>) {
    onChange(blocks.map((block, blockIndex) => (blockIndex === index ? { ...block, ...patch } : block)));
  }

  return (
    <fieldset className="manual-report-section">
      <div className="manual-list-heading">
        <div>
          <p className="eyebrow">Report content</p>
          <h4>Meaningful sections</h4>
        </div>
        <button
          className="inline-add-button"
          type="button"
          onClick={() =>
            onChange([
              ...blocks,
              {
                block_key: `custom-${Date.now()}`,
                title: "New section",
                text: "",
              },
            ])
          }
        >
          Add section
        </button>
      </div>
      <p className="field-help">
        The sections are intentionally broad. Paste complete paragraphs or lists into the section
        where they make the most sense; the agent will place the content into the Canva template.
      </p>
      <div className="manual-report-content-blocks">
        {blocks.map((block, index) => (
          <article className="manual-report-content-block" key={block.block_key || index}>
            <div className="manual-report-content-block-heading">
              <label className="manual-field">
                <span>Section name</span>
                <input
                  value={block.title}
                  onChange={(event) => updateBlock(index, { title: event.target.value })}
                />
              </label>
              <button
                className="inline-remove-button"
                type="button"
                onClick={() => onChange(blocks.filter((_, blockIndex) => blockIndex !== index))}
              >
                Remove
              </button>
            </div>
            <label className="manual-field">
              <span>Content</span>
              <textarea
                value={block.text}
                onChange={(event) => updateBlock(index, { text: event.target.value })}
                placeholder={`Paste the ${block.title.toLowerCase()} content here...`}
              />
            </label>
          </article>
        ))}
      </div>
    </fieldset>
  );
}

function ImageGroupsEditor({
  clientId,
  submissionId,
  groups,
  onChange,
}: {
  clientId: string;
  submissionId: string;
  groups: ManualReportImageGroup[];
  onChange: (groups: ManualReportImageGroup[]) => void;
}) {
  const [uploadingGroupKey, setUploadingGroupKey] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);

  function updateGroup(index: number, patch: Partial<ManualReportImageGroup>) {
    onChange(groups.map((group, groupIndex) => (groupIndex === index ? { ...group, ...patch } : group)));
  }

  async function uploadImages(index: number, files: File[]) {
    if (files.length === 0) return;
    const group = groups[index];
    if (!group) return;
    setUploadingGroupKey(group.group_key);
    setUploadError(null);
    try {
      const uploaded = await Promise.all(
        files.map((file) => uploadManualReportImage(clientId, submissionId, file)),
      );
      updateGroup(index, {
        images: [...group.images, ...uploaded],
        asset_keys: [...group.asset_keys, ...uploaded.map((image) => image.asset_key)],
      });
    } catch (requestError: unknown) {
      setUploadError(requestError instanceof Error ? requestError.message : "Image upload failed");
    } finally {
      setUploadingGroupKey(null);
    }
  }

  return (
    <fieldset className="manual-report-section">
      <div className="manual-list-heading">
        <div>
          <p className="eyebrow">Optional visual references</p>
          <h4>Image groups</h4>
        </div>
        <button
          className="inline-add-button"
          type="button"
          onClick={() =>
            onChange([
              ...groups,
              {
                group_key: `group-${Date.now()}`,
                label: "New image group",
                instructions: "",
                images: [],
                asset_keys: [],
              },
            ])
          }
        >
          Add group
        </button>
      </div>
      <p className="field-help">
        Groups are empty by default. Add your own photos to each group, then select which ones the
        agent may use. Questionnaire photos are not added automatically.
      </p>
      {uploadError ? <p className="error-text">{uploadError}</p> : null}
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
                  placeholder="e.g. Two outfit references"
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
            <label className="manual-report-add-images">
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp,image/gif"
                multiple
                disabled={uploadingGroupKey === group.group_key}
                onChange={(event) => {
                  void uploadImages(index, [...(event.target.files ?? [])]);
                  event.target.value = "";
                }}
              />
              {uploadingGroupKey === group.group_key ? "Uploading..." : "Add photos"}
            </label>
            <div className="manual-report-asset-picker">
              <span className="manual-field-label">Choose images for this group</span>
              {group.images.length === 0 ? (
                <p className="gallery-empty">No photos added to this group.</p>
              ) : null}
              {group.images.map((image) => (
                <ImageChoice
                  key={image.asset_key}
                  image={image}
                  selected={group.asset_keys.includes(image.asset_key)}
                  onToggle={() => {
                    const asset_keys = group.asset_keys.includes(image.asset_key)
                      ? group.asset_keys.filter((key) => key !== image.asset_key)
                      : [...group.asset_keys, image.asset_key];
                    updateGroup(index, { asset_keys });
                  }}
                />
              ))}
            </div>
          </article>
        ))}
      </div>
    </fieldset>
  );
}

function ImageChoice({
  image,
  selected,
  onToggle,
}: {
  image: ManualReportImage;
  selected: boolean;
  onToggle: () => void;
}) {
  return (
    <label className={`manual-report-asset-option${selected ? " is-selected" : ""}`}>
      <input type="checkbox" checked={selected} onChange={onToggle} />
      <img src={`${API_BASE_URL}${image.url}`} alt="" loading="lazy" />
      <span>{image.filename}</span>
    </label>
  );
}

function ManualReportPreview({ draft }: { draft: ManualStyleReportContent }) {
  const firstLine = draft.content_blocks.find((block) => block.text.trim())?.title || "Signature Style Report";
  const filledBlocks = draft.content_blocks.filter((block) => block.text.trim()).slice(0, 6);

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
        {filledBlocks.length > 0 ? (
          filledBlocks.map((block) => (
            <section key={block.block_key}>
              <h5>{block.title}</h5>
              <p>{block.text}</p>
            </section>
          ))
        ) : (
          <p className="preview-placeholder">Your report preview will appear here as you type.</p>
        )}
      </div>
      <div className="manual-report-preview-groups">
        {draft.image_groups.map((group) => {
          const selectedImages = group.images.filter((image) => group.asset_keys.includes(image.asset_key));
          return (
            <section className="manual-report-preview-group" key={group.group_key}>
              <h5>{group.label || "Untitled image group"}</h5>
              {group.instructions ? <p>{group.instructions}</p> : null}
              <div className="manual-report-preview-images">
                {selectedImages.map((image) => (
                  <img
                    key={image.asset_key}
                    src={`${API_BASE_URL}${image.url}`}
                    alt={`${group.label || "Image group"}: ${image.filename}`}
                  />
                ))}
                {selectedImages.length === 0 ? <span>No images selected</span> : null}
              </div>
            </section>
          );
        })}
      </div>
      <p className="field-help">
        This is an editor preview. The final Canva layout is created after the placement agent maps
        the text and selected images to the template.
      </p>
    </aside>
  );
}

function mergeWithEmptyContent(content: ManualStyleReportContent | null): ManualStyleReportContent {
  const empty = createEmptyManualStyleReport();
  const content_blocks = content?.content_blocks?.length
    ? content.content_blocks
    : content?.source_text?.trim()
      ? [{ ...empty.content_blocks[0], text: content.source_text }]
      : empty.content_blocks;
  const image_groups = (content?.image_groups ?? []).map((group) => ({
    ...group,
    images: group.images ?? [],
    asset_keys: group.images?.length ? group.asset_keys ?? [] : [],
  }));
  return {
    ...empty,
    ...content,
    source_text: content?.source_text ?? "",
    content_blocks,
    image_groups,
  };
}
