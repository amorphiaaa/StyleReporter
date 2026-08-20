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
};

export type GenerateStyleReportRequest = {
  submission_id: string;
  runtime?: StyleReportRuntimeType;
};

export type StyleReportRuntimeType = "stub" | "agents_sdk_dry_run";

export type StyleReportResponse = {
  id: string;
  client_id: string;
  submission_id: string;
  status: string;
  runtime_type: string;
  report_version: string;
  report: Record<string, unknown> | null;
  error_message: string | null;
  created_at: string | null;
  started_at: string | null;
  completed_at: string | null;
};
