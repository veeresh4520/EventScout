export type SourceStatus =
  | "PENDING"
  | "DISCOVERING"
  | "TESTING"
  | "READY_FOR_REVIEW"
  | "ENABLED"
  | "DISABLED"
  | "FAILED"
  | "NEEDS_REDISCOVERY";

export interface Source {
  id: string;
  _id?: string;
  name: string;
  base_url?: string;
  event_list_url?: string;
  url: string;
  source_type?: string;
  status: SourceStatus;
  discovery_status?: string;
  collection_strategy?: string;
  strategy?: string;
  configuration?: Record<string, any>;
  field_mapping?: Record<string, any>;
  sample_events?: any[];
  confidence_score?: number;
  notes?: string;
  enabled: boolean;
  last_scraped_at?: string | null;
  last_success_at?: string | null;
  last_error?: string | null;
  consecutive_failures?: number;
  events_found_last_run?: number;
  created_by?: string;
  created_at: string;
  updated_at: string;
}

export interface SourcesOverview {
  total_sources: number;
  enabled: number;
  pending_review: number;
  discovering: number;
  failed: number;
  disabled: number;
}
