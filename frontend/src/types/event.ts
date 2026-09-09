export interface Event {
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
}
