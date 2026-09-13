export interface Event {
  id?: string;
  _id?: string;
  title: string;
  event_url: string;
  date_time: string;
  organizer: string;
  source: string;
  mode_location: string;
  city: string | null;
  country: string | null;
  poster_image_url: string | null;
  description: string | null;
  is_free: boolean;
  price_amount: number | null;
  price_currency: string | null;
  source_event_id: string | null;
  registration_url: string | null;
  is_technical: boolean;
  categories: string[];
  scraped_at: string;
  
  // Intelligent Ranking & Host Reputation Fields
  ranking_score?: number;
  why_recommended?: string[];
  host_tier?: string;
  host_badge?: string;
  host_verified?: boolean;
  score_breakdown?: {
    organization_score?: number;
    quality_score?: number;
    personalization_score?: number;
    urgency_score?: number;
  };
}
