export interface NotificationItem {
  id: string;
  _id?: string;
  user_id: string;
  event_id: string;
  type: string;
  title: string;
  message: string;
  event_url?: string;
  read: boolean;
  metadata?: {
    organizer?: string;
    location?: string;
    date_time?: string;
    categories?: string[];
  };
  created_at: string;
}

export interface NotificationsResponse {
  notifications: NotificationItem[];
  unread_count: number;
}
