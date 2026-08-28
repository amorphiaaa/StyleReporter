import { useEffect, useState } from "react";
import type { Dispatch, FormEvent, SetStateAction } from "react";

import { saveManualStyleReport } from "../api/client";
import type {
  ActionPlanItem,
  BrandCategory,
  GuidanceSection,
  ManualStyleReportContent,
  MoodboardItem,
  NamedListSection,
  OutfitFormula,
  PaletteColor,
  PaletteSection,
  SilhouetteItem,
  SilhouetteSection,
  StyleAnchor,
} from "../types";

const PALETTE_SECTIONS = [
  ["foundation", "Foundation colours (bottoms / outerwear)"],
  ["accent", "Accent colours (accessories)"],
  ["portrait", "Portrait colours (tops)"],
] as const;

const ACCESSORY_CATEGORIES = [
  "Eyewear",
  "Watches",
  "Bags",
  "Jewellery / Belts",
  "Scarves",
  "Shoes",
];

const BRAND_CATEGORIES = [
  "Coats & jackets",
  "Bottoms",
  "Knitwear",
  "Dresses",
  "Shirts & blouses / T-shirts",
  "Denim",
  "Jewellery",
  "Accessories",
  "Sunglasses",
  "Bags",
  "Shoes",
];

export function createEmptyManualStyleReport(): ManualStyleReportContent {
  return {
    how_to_use: { intro: "", items: ["", "", ""] },
    title: "",
    alignment_summary: "",
    current_style_language: ["", "", "", "", ""],
    desired_style_language: ["", "", "", "", ""],
    disconnect: "",
    style_language_summary: "",
    style_language_anchors: ["", "", ""],
    color_palette: Object.fromEntries(
      PALETTE_SECTIONS.map(([key]) => [key, { intro: "", colors: [] }]),
    ),
    prints_and_textures: { intro: "", what_works: [""], how_to_use: ["", "", ""] },
    silhouettes: {
      intro: "",
      outer_layers: [],
      bottoms: [],
      tops_and_knitwear: [],
      dresses: [],
    },
    accessories: {
      intro: "",
      core_elements: [""],
      use_principles: ["", ""],
      categories: ACCESSORY_CATEGORIES.map((name) => ({ name, items: [""] })),
    },
    outfit_formulas: [emptyOutfitFormula(), emptyOutfitFormula(), emptyOutfitFormula(), emptyOutfitFormula()],
    style_anchors: [emptyStyleAnchor(), emptyStyleAnchor(), emptyStyleAnchor(), emptyStyleAnchor()],
    what_can_distract: {
      intro: "",
      colors: [""],
      prints: [""],
      silhouettes: [""],
    },
    brands: BRAND_CATEGORIES.map((category) => ({ category, brands: [""] })),
    moodboard: [emptyMoodboardItem(), emptyMoodboardItem(), emptyMoodboardItem()],
    action_plan: [emptyActionPlanItem(), emptyActionPlanItem(), emptyActionPlanItem()],
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
            Write the report yourself using the sections from the reference portfolio. Nothing
            here is generated automatically.
          </p>
        </div>
        <div className="manual-report-save-status" aria-live="polite">
          {saveError ? <span className="error-text">{saveError}</span> : null}
          {savedAt ? <span>Saved at {savedAt}</span> : null}
        </div>
      </div>

      <fieldset className="manual-report-section">
        <legend>How to use your Signature Style Report</legend>
        <TextAreaField
          label="Introduction"
          value={draft.how_to_use.intro}
          onChange={(value) => updateSection(setDraft, "how_to_use", { intro: value })}
        />
        <StringListEditor
          label="Principles / reminders"
          values={draft.how_to_use.items}
          onChange={(items) => updateSection(setDraft, "how_to_use", { items })}
        />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Signature Style Alignment</legend>
        <TextInputField
          label="Style Language title"
          value={draft.title}
          onChange={(title) => setDraft((current) => ({ ...current, title }))}
          placeholder="e.g. Feminine Creative Style Language"
        />
        <TextAreaField
          label="Alignment summary"
          value={draft.alignment_summary}
          onChange={(alignment_summary) => setDraft((current) => ({ ...current, alignment_summary }))}
        />
        <div className="manual-report-two-column">
          <StringListEditor
            label="Current Style Language"
            values={draft.current_style_language}
            onChange={(current_style_language) =>
              setDraft((current) => ({ ...current, current_style_language }))
            }
          />
          <StringListEditor
            label="Desired Style Language"
            values={draft.desired_style_language}
            onChange={(desired_style_language) =>
              setDraft((current) => ({ ...current, desired_style_language }))
            }
          />
        </div>
        <TextAreaField
          label="The Disconnect"
          value={draft.disconnect}
          onChange={(disconnect) => setDraft((current) => ({ ...current, disconnect }))}
        />
        <TextAreaField
          label="Style Language summary"
          value={draft.style_language_summary}
          onChange={(style_language_summary) =>
            setDraft((current) => ({ ...current, style_language_summary }))
          }
        />
        <StringListEditor
          label="Style Language anchors"
          values={draft.style_language_anchors}
          onChange={(style_language_anchors) =>
            setDraft((current) => ({ ...current, style_language_anchors }))
          }
        />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Colour Palette</legend>
        {PALETTE_SECTIONS.map(([key, label]) => (
          <PaletteSectionEditor
            key={key}
            label={label}
            section={draft.color_palette[key] ?? emptyPaletteSection()}
            onChange={(section) =>
              setDraft((current) => ({
                ...current,
                color_palette: { ...current.color_palette, [key]: section },
              }))
            }
          />
        ))}
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Prints &amp; Textures</legend>
        <GuidanceEditor
          section={draft.prints_and_textures}
          onChange={(prints_and_textures) => setDraft((current) => ({ ...current, prints_and_textures }))}
          firstListLabel="What works for you"
          secondListLabel="How to use prints and textures"
        />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Key Silhouettes</legend>
        <TextAreaField
          label="The shape of your style"
          value={draft.silhouettes.intro}
          onChange={(intro) => updateSection(setDraft, "silhouettes", { intro })}
        />
        <SilhouetteGroupEditor
          label="Outer layers"
          items={draft.silhouettes.outer_layers}
          onChange={(outer_layers) => updateSection(setDraft, "silhouettes", { outer_layers })}
        />
        <SilhouetteGroupEditor
          label="Bottoms"
          items={draft.silhouettes.bottoms}
          onChange={(bottoms) => updateSection(setDraft, "silhouettes", { bottoms })}
        />
        <SilhouetteGroupEditor
          label="Tops & knitwear"
          items={draft.silhouettes.tops_and_knitwear}
          onChange={(tops_and_knitwear) => updateSection(setDraft, "silhouettes", { tops_and_knitwear })}
        />
        <SilhouetteGroupEditor
          label="Dresses"
          items={draft.silhouettes.dresses}
          onChange={(dresses) => updateSection(setDraft, "silhouettes", { dresses })}
        />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Accessories</legend>
        <TextAreaField
          label="Core elements introduction"
          value={draft.accessories.intro}
          onChange={(intro) => updateSection(setDraft, "accessories", { intro })}
        />
        <StringListEditor
          label="Core elements"
          values={draft.accessories.core_elements}
          onChange={(core_elements) => updateSection(setDraft, "accessories", { core_elements })}
        />
        <StringListEditor
          label="Use principles"
          values={draft.accessories.use_principles}
          onChange={(use_principles) => updateSection(setDraft, "accessories", { use_principles })}
        />
        <NamedListEditor
          label="Accessory categories"
          sections={draft.accessories.categories}
          onChange={(categories) => updateSection(setDraft, "accessories", { categories })}
        />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Outfit Formulas</legend>
        <div className="manual-report-repeat-list">
          {draft.outfit_formulas.map((formula, index) => (
            <OutfitFormulaEditor
              key={index}
              index={index}
              formula={formula}
              onChange={(next) => updateAt(setDraft, "outfit_formulas", index, next)}
              onRemove={() => removeAt(setDraft, "outfit_formulas", index)}
            />
          ))}
        </div>
        <AddButton label="Add outfit formula" onClick={() => appendTo(setDraft, "outfit_formulas", emptyOutfitFormula())} />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Your Style Anchors</legend>
        <div className="manual-report-repeat-list">
          {draft.style_anchors.map((anchor, index) => (
            <StyleAnchorEditor
              key={index}
              index={index}
              anchor={anchor}
              onChange={(next) => updateAt(setDraft, "style_anchors", index, next)}
              onRemove={() => removeAt(setDraft, "style_anchors", index)}
            />
          ))}
        </div>
        <AddButton label="Add style anchor" onClick={() => appendTo(setDraft, "style_anchors", emptyStyleAnchor())} />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>What Can Distract From Your Style</legend>
        <TextAreaField
          label="Introduction"
          value={draft.what_can_distract.intro}
          onChange={(intro) => updateSection(setDraft, "what_can_distract", { intro })}
        />
        <div className="manual-report-three-column">
          <StringListEditor
            label="Colours"
            values={draft.what_can_distract.colors}
            onChange={(colors) => updateSection(setDraft, "what_can_distract", { colors })}
          />
          <StringListEditor
            label="Prints"
            values={draft.what_can_distract.prints}
            onChange={(prints) => updateSection(setDraft, "what_can_distract", { prints })}
          />
          <StringListEditor
            label="Silhouettes"
            values={draft.what_can_distract.silhouettes}
            onChange={(silhouettes) => updateSection(setDraft, "what_can_distract", { silhouettes })}
          />
        </div>
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Brands That Speak Your Language</legend>
        <NamedListEditor
          label="Brand categories"
          sections={draft.brands.map((entry) => ({ name: entry.category, items: entry.brands }))}
          onChange={(sections) =>
            setDraft((current) =>
              ({ ...current, brands: sections.map((entry) => ({ category: entry.name, brands: entry.items })) }),
            )
          }
          itemLabel="Brands"
        />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Your Mood Board</legend>
        <div className="manual-report-repeat-list">
          {draft.moodboard.map((item, index) => (
            <MoodboardEditor
              key={index}
              index={index}
              item={item}
              onChange={(next) => updateAt(setDraft, "moodboard", index, next)}
              onRemove={() => removeAt(setDraft, "moodboard", index)}
            />
          ))}
        </div>
        <AddButton label="Add moodboard link" onClick={() => appendTo(setDraft, "moodboard", emptyMoodboardItem())} />
      </fieldset>

      <fieldset className="manual-report-section">
        <legend>Your Action Plan</legend>
        <div className="manual-report-repeat-list">
          {draft.action_plan.map((item, index) => (
            <ActionPlanEditor
              key={index}
              index={index}
              item={item}
              onChange={(next) => updateAt(setDraft, "action_plan", index, next)}
              onRemove={() => removeAt(setDraft, "action_plan", index)}
            />
          ))}
        </div>
        <AddButton label="Add action" onClick={() => appendTo(setDraft, "action_plan", emptyActionPlanItem())} />
      </fieldset>

      <div className="manual-report-submit-row">
        <span>Save a draft at any point. The report remains editable.</span>
        <button className="primary-button" type="submit" disabled={isSaving}>
          {isSaving ? "Saving..." : "Save manual report"}
        </button>
      </div>
    </form>
  );
}

function TextInputField({
  label,
  value,
  onChange,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <label className="manual-field">
      <span>{label}</span>
      <input value={value} placeholder={placeholder} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function TextAreaField({ label, value, onChange }: { label: string; value: string; onChange: (value: string) => void }) {
  return (
    <label className="manual-field">
      <span>{label}</span>
      <textarea rows={4} value={value} onChange={(event) => onChange(event.target.value)} />
    </label>
  );
}

function StringListEditor({
  label,
  values,
  onChange,
}: {
  label: string;
  values: string[];
  onChange: (values: string[]) => void;
}) {
  return (
    <div className="manual-list-editor">
      <div className="manual-list-heading">
        <span>{label}</span>
        <AddButton label="Add" onClick={() => onChange([...values, ""])} />
      </div>
      {values.map((value, index) => (
        <div className="manual-list-row" key={index}>
          <input
            aria-label={`${label} ${index + 1}`}
            value={value}
            onChange={(event) => {
              const next = [...values];
              next[index] = event.target.value;
              onChange(next);
            }}
          />
          <RemoveButton onClick={() => onChange(values.filter((_, itemIndex) => itemIndex !== index))} />
        </div>
      ))}
    </div>
  );
}

function GuidanceEditor({
  section,
  onChange,
  firstListLabel,
  secondListLabel,
}: {
  section: GuidanceSection;
  onChange: (section: GuidanceSection) => void;
  firstListLabel: string;
  secondListLabel: string;
}) {
  return (
    <>
      <TextAreaField label="Introduction" value={section.intro} onChange={(intro) => onChange({ ...section, intro })} />
      <div className="manual-report-two-column">
        <StringListEditor
          label={firstListLabel}
          values={section.what_works}
          onChange={(what_works) => onChange({ ...section, what_works })}
        />
        <StringListEditor
          label={secondListLabel}
          values={section.how_to_use}
          onChange={(how_to_use) => onChange({ ...section, how_to_use })}
        />
      </div>
    </>
  );
}

function PaletteSectionEditor({
  label,
  section,
  onChange,
}: {
  label: string;
  section: PaletteSection;
  onChange: (section: PaletteSection) => void;
}) {
  return (
    <div className="manual-subsection">
      <h5>{label}</h5>
      <TextAreaField label="Section description" value={section.intro} onChange={(intro) => onChange({ ...section, intro })} />
      <div className="manual-report-repeat-list">
        {section.colors.map((color, index) => (
          <div className="manual-repeat-card" key={index}>
            <div className="manual-repeat-card-heading">
              <strong>Colour {index + 1}</strong>
              <RemoveButton onClick={() => onChange({ ...section, colors: section.colors.filter((_, i) => i !== index) })} />
            </div>
            <div className="manual-report-two-column">
              <TextInputField label="Name" value={color.name} onChange={(name) => updateColor(section, onChange, index, { name })} />
              <TextInputField label="HEX" value={color.hex} onChange={(hex) => updateColor(section, onChange, index, { hex })} placeholder="#B23B32" />
            </div>
            <TextAreaField label="Description" value={color.description} onChange={(description) => updateColor(section, onChange, index, { description })} />
            <TextAreaField label="Works beautifully with" value={color.works_with} onChange={(works_with) => updateColor(section, onChange, index, { works_with })} />
          </div>
        ))}
      </div>
      <AddButton label="Add colour" onClick={() => onChange({ ...section, colors: [...section.colors, emptyPaletteColor()] })} />
    </div>
  );
}

function SilhouetteGroupEditor({ label, items, onChange }: { label: string; items: SilhouetteItem[]; onChange: (items: SilhouetteItem[]) => void }) {
  return (
    <div className="manual-subsection">
      <h5>{label}</h5>
      {items.map((item, index) => (
        <div className="manual-repeat-card" key={index}>
          <div className="manual-repeat-card-heading">
            <strong>{label} {index + 1}</strong>
            <RemoveButton onClick={() => onChange(items.filter((_, i) => i !== index))} />
          </div>
          <TextInputField label="Name" value={item.name} onChange={(name) => updateItem(items, onChange, index, { name })} />
          <TextAreaField label="Description" value={item.description} onChange={(description) => updateItem(items, onChange, index, { description })} />
        </div>
      ))}
      <AddButton label={`Add ${label.toLowerCase()}`} onClick={() => onChange([...items, { name: "", description: "" }])} />
    </div>
  );
}

function NamedListEditor({
  label,
  sections,
  onChange,
  itemLabel = "Items",
}: {
  label: string;
  sections: NamedListSection[];
  onChange: (sections: NamedListSection[]) => void;
  itemLabel?: string;
}) {
  return (
    <div className="manual-subsection">
      <div className="manual-list-heading">
        <h5>{label}</h5>
        <AddButton label="Add category" onClick={() => onChange([...sections, { name: "", items: [""] }])} />
      </div>
      {sections.map((section, index) => (
        <div className="manual-repeat-card" key={index}>
          <div className="manual-repeat-card-heading">
            <TextInputField label="Category" value={section.name} onChange={(name) => updateItem(sections, onChange, index, { name })} />
            <RemoveButton onClick={() => onChange(sections.filter((_, i) => i !== index))} />
          </div>
          <StringListEditor
            label={itemLabel}
            values={section.items}
            onChange={(items) => updateItem(sections, onChange, index, { items })}
          />
        </div>
      ))}
    </div>
  );
}

function OutfitFormulaEditor({ index, formula, onChange, onRemove }: { index: number; formula: OutfitFormula; onChange: (formula: OutfitFormula) => void; onRemove: () => void }) {
  return (
    <div className="manual-repeat-card">
      <div className="manual-repeat-card-heading">
        <strong>Formula {index + 1}</strong>
        <RemoveButton onClick={onRemove} />
      </div>
      <TextInputField label="Formula name" value={formula.name} onChange={(name) => onChange({ ...formula, name })} />
      <TextInputField label="Occasions" value={formula.occasions.join(", ")} onChange={(value) => onChange({ ...formula, occasions: splitCommaList(value) })} placeholder="Every day, Lunch" />
      <TextAreaField label="Logic" value={formula.logic} onChange={(logic) => onChange({ ...formula, logic })} />
      <StringListEditor label="How to build the outfit" values={formula.steps} onChange={(steps) => onChange({ ...formula, steps })} />
    </div>
  );
}

function StyleAnchorEditor({ index, anchor, onChange, onRemove }: { index: number; anchor: StyleAnchor; onChange: (anchor: StyleAnchor) => void; onRemove: () => void }) {
  return (
    <div className="manual-repeat-card">
      <div className="manual-repeat-card-heading">
        <strong>Anchor {index + 1}</strong>
        <RemoveButton onClick={onRemove} />
      </div>
      <TextInputField label="Name" value={anchor.name} onChange={(name) => onChange({ ...anchor, name })} />
      <TextAreaField label="Description" value={anchor.description} onChange={(description) => onChange({ ...anchor, description })} />
    </div>
  );
}

function MoodboardEditor({ index, item, onChange, onRemove }: { index: number; item: MoodboardItem; onChange: (item: MoodboardItem) => void; onRemove: () => void }) {
  return (
    <div className="manual-repeat-card">
      <div className="manual-repeat-card-heading">
        <strong>Reference {index + 1}</strong>
        <RemoveButton onClick={onRemove} />
      </div>
      <div className="manual-report-two-column">
        <TextInputField label="Label / source" value={item.label} onChange={(label) => onChange({ ...item, label })} />
        <TextInputField label="Image URL" value={item.url} onChange={(url) => onChange({ ...item, url })} placeholder="https://..." />
      </div>
      <TextAreaField label="Note" value={item.note} onChange={(note) => onChange({ ...item, note })} />
    </div>
  );
}

function ActionPlanEditor({ index, item, onChange, onRemove }: { index: number; item: ActionPlanItem; onChange: (item: ActionPlanItem) => void; onRemove: () => void }) {
  return (
    <div className="manual-repeat-card">
      <div className="manual-repeat-card-heading">
        <strong>Action {index + 1}</strong>
        <RemoveButton onClick={onRemove} />
      </div>
      <TextInputField label="Action title" value={item.title} onChange={(title) => onChange({ ...item, title })} />
      <TextAreaField label="Action text" value={item.body} onChange={(body) => onChange({ ...item, body })} />
    </div>
  );
}

function AddButton({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button className="inline-add-button" type="button" onClick={onClick}>
      + {label}
    </button>
  );
}

function RemoveButton({ onClick }: { onClick: () => void }) {
  return (
    <button className="inline-remove-button" type="button" onClick={onClick} aria-label="Remove item">
      Remove
    </button>
  );
}

function updateSection<K extends keyof ManualStyleReportContent>(
  setDraft: Dispatch<SetStateAction<ManualStyleReportContent>>,
  key: K,
  patch: Partial<ManualStyleReportContent[K]>,
) {
  setDraft((current) => {
    const section = current[key];
    if (!section || typeof section !== "object") return current;
    return {
      ...current,
      [key]: { ...(section as Record<string, unknown>), ...(patch as Record<string, unknown>) },
    } as ManualStyleReportContent;
  });
}

function updateAt<K extends keyof ManualStyleReportContent>(
  setDraft: Dispatch<SetStateAction<ManualStyleReportContent>>,
  key: K,
  index: number,
  value: ManualStyleReportContent[K] extends Array<infer Item> ? Item : never,
) {
  setDraft((current) => {
    const values = current[key];
    if (!Array.isArray(values)) return current;
    const next = [...values];
    next[index] = value;
    return { ...current, [key]: next };
  });
}

function appendTo<K extends keyof ManualStyleReportContent>(
  setDraft: Dispatch<SetStateAction<ManualStyleReportContent>>,
  key: K,
  value: ManualStyleReportContent[K] extends Array<infer Item> ? Item : never,
) {
  setDraft((current) => {
    const values = current[key];
    if (!Array.isArray(values)) return current;
    return { ...current, [key]: [...values, value] };
  });
}

function removeAt<K extends keyof ManualStyleReportContent>(
  setDraft: Dispatch<SetStateAction<ManualStyleReportContent>>,
  key: K,
  index: number,
) {
  setDraft((current) => {
    const values = current[key];
    if (!Array.isArray(values)) return current;
    return { ...current, [key]: values.filter((_, itemIndex) => itemIndex !== index) };
  });
}

function updateColor(section: PaletteSection, onChange: (section: PaletteSection) => void, index: number, patch: Partial<PaletteColor>) {
  const colors = [...section.colors];
  colors[index] = { ...colors[index], ...patch };
  onChange({ ...section, colors });
}

function updateItem<T extends object>(items: T[], onChange: (items: T[]) => void, index: number, patch: Partial<T>) {
  const next = [...items];
  next[index] = { ...next[index], ...patch };
  onChange(next);
}

function splitCommaList(value: string): string[] {
  return value.split(",").map((item) => item.trim()).filter(Boolean);
}

function emptyPaletteSection(): PaletteSection {
  return { intro: "", colors: [] };
}

function emptyPaletteColor(): PaletteColor {
  return { name: "", hex: "", description: "", works_with: "" };
}

function emptyOutfitFormula(): OutfitFormula {
  return { name: "", occasions: [], logic: "", steps: [""] };
}

function emptyStyleAnchor(): StyleAnchor {
  return { name: "", description: "" };
}

function emptyMoodboardItem(): MoodboardItem {
  return { label: "", url: "", note: "" };
}

function emptyActionPlanItem(): ActionPlanItem {
  return { title: "", body: "" };
}

function mergeWithEmptyContent(content: ManualStyleReportContent | null): ManualStyleReportContent {
  const empty = createEmptyManualStyleReport();
  if (!content) return empty;
  return {
    ...empty,
    ...content,
    how_to_use: { ...empty.how_to_use, ...content.how_to_use },
    silhouettes: { ...empty.silhouettes, ...content.silhouettes } as SilhouetteSection,
    accessories: { ...empty.accessories, ...content.accessories },
    prints_and_textures: { ...empty.prints_and_textures, ...content.prints_and_textures },
    what_can_distract: { ...empty.what_can_distract, ...content.what_can_distract },
    color_palette: { ...empty.color_palette, ...content.color_palette },
  };
}
