export interface NotificationPreferences {
  dashboard_enabled: boolean;
  browser_enabled: boolean;
  email_enabled: boolean;
}

export interface User {
  id: string;
  username: string;
  email: string;
  interests: string[];
  skills: string[];
  preferred_event_types: string[];
  preferred_modes: string[];
  saved_event_ids: string[];
  is_admin?: boolean;
  notification_preferences?: NotificationPreferences;
  created_at: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Preferences {
  interests: string[];
  skills: string[];
  preferred_event_types: string[];
  preferred_modes: string[];
  notification_preferences?: NotificationPreferences;
}

