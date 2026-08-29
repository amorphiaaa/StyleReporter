export type HealthResponse = {
  status: "ok";
  service: string;
  stage: "scaffold";
};

export type ImportRow = {
  row_number: number;
  values: Record<string, string>;
};

export type ManualImportRequest = {
  spreadsheet_id: string;
  sheet_name: string;
  cell_range?: string;
  email_header: string;
  display_name_header?: string;
  timestamp_header?: string;
  source_type?: string;
  questionnaire_version?: string;
  rows: ImportRow[];
};

export type ImportError = {
  row_number: number;
  code: string;
  message: string;
};

export type ImportResponse = {
  import_id: string;
  rows_seen: number;
  created_clients: number;
  updated_clients: number;
  created_submissions: number;
  rejected_rows: number;
  skipped_duplicates: number;
  errors: ImportError[];
};

export type ImportRunResponse = {
  import_id: string;
  source_type: string;
  spreadsheet_id: string;
  sheet_name: string;
  status: string;
  rows_seen: number;
  created_clients: number;
  updated_clients: number;
  created_submissions: number;
  rejected_rows: number;
  skipped_duplicates: number;
  row_errors: ImportError[];
  started_at: string;
  completed_at: string | null;
};

export type ImportHistoryItem = {
  import_id: string;
  source_type: string;
  spreadsheet_id: string;
  sheet_name: string;
  status: string;
  rows_seen: number;
  created_clients: number;
  updated_clients: number;
  created_submissions: number;
  rejected_rows: number;
  skipped_duplicates: number;
  row_errors_count: number;
  started_at: string;
  completed_at: string | null;
};

export type ClientListItem = {
  id: string;
  email_normalized: string;
  display_name: string | null;
  submission_count: number;
};

export type ClientSubmission = {
  id: string;
  source_type: string;
  spreadsheet_id: string;
  sheet_name: string;
  source_row_number: number;
  source_row_hash: string;
  questionnaire_version: string | null;
  submitted_at: string | null;
  imported_at: string | null;
  raw_payload: Record<string, unknown>;
};

export type ClientDetail = {
  id: string;
  email_normalized: string;
  display_name: string | null;
  submissions: ClientSubmission[];
  assets: ClientAsset[];
};

export type ClientAsset = {
  submission_id: string;
  field_key: string;
  ordinal: number;
  folder_key: string;
  folder_label: string;
  filename: string;
  content_type: string;
  url: string;
};

export type UpdateClientRequest = {
  display_name: string | null;
};

export type ClientUpdateResponse = {
  id: string;
  email_normalized: string;
  display_name: string | null;
};

export type ReportTextBlock = {
  intro: string;
  items: string[];
};

export type PaletteColor = {
  name: string;
  hex: string;
  description: string;
  works_with: string;
};

export type PaletteSection = {
  intro: string;
  colors: PaletteColor[];
};

export type GuidanceSection = {
  intro: string;
  what_works: string[];
  how_to_use: string[];
};

export type SilhouetteItem = {
  name: string;
  description: string;
};

export type SilhouetteSection = {
  intro: string;
  outer_layers: SilhouetteItem[];
  bottoms: SilhouetteItem[];
  tops_and_knitwear: SilhouetteItem[];
  dresses: SilhouetteItem[];
};

export type NamedListSection = {
  name: string;
  items: string[];
};

export type AccessoriesSection = {
  intro: string;
  core_elements: string[];
  use_principles: string[];
  categories: NamedListSection[];
};

export type OutfitFormula = {
  name: string;
  occasions: string[];
  logic: string;
  steps: string[];
};

export type StyleAnchor = {
  name: string;
  description: string;
};

export type DistractionSection = {
  intro: string;
  colors: string[];
  prints: string[];
  silhouettes: string[];
};

export type BrandCategory = {
  category: string;
  brands: string[];
};

export type MoodboardItem = {
  label: string;
  url: string;
  note: string;
};

export type ActionPlanItem = {
  title: string;
  body: string;
};

export type ManualReportImageGroup = {
  group_key: string;
  label: string;
  instructions: string;
  images: ManualReportImage[];
  asset_keys: string[];
};

export type ManualReportImage = {
  asset_key: string;
  filename: string;
  url: string;
};

export type ManualStyleReportContent = {
  source_text: string;
  image_groups: ManualReportImageGroup[];
  how_to_use: ReportTextBlock;
  title: string;
  alignment_summary: string;
  current_style_language: string[];
  desired_style_language: string[];
  disconnect: string;
  style_language_summary: string;
  style_language_anchors: string[];
  color_palette: Record<string, PaletteSection>;
  prints_and_textures: GuidanceSection;
  silhouettes: SilhouetteSection;
  accessories: AccessoriesSection;
  outfit_formulas: OutfitFormula[];
  style_anchors: StyleAnchor[];
  what_can_distract: DistractionSection;
  brands: BrandCategory[];
  moodboard: MoodboardItem[];
  action_plan: ActionPlanItem[];
};

export type ManualStyleReportResponse = {
  id: string;
  client_id: string;
  submission_id: string;
  content: ManualStyleReportContent;
  created_at: string | null;
  updated_at: string | null;
};

export type CanvaReportResponse = {
  status: "success" | "failed";
  autofill_job_id: string;
  design_id: string | null;
  design_url: string | null;
  export_job_id: string | null;
  pdf_url: string | null;
  text_fields_filled: number;
  image_fields_filled: number;
};
