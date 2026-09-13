# EventScout — Data Model & Personalization Architecture

**Document Version:** 1.0  
**Phase:** Group 1 — Personalization Foundation (Authentication, Preferences, Saved Events)  
**Database:** MongoDB Atlas  

---

## 1. Executive Summary

EventScout connects tech enthusiasts to curated technical events, workshops, and hackathons. This document specifies the data model and architectural decisions for **Group 1: Personalization Foundation**, covering:
1. **User Identity & Authentication** (Secure registration, login, bcrypt password hashing, and JWT tokens).
2. **User Preferences** (Interests, skills, preferred event formats, and delivery modes).
3. **Saved Events System** (User-specific bookmarking with idempotent operations).
4. **Data Isolation & Security** (Strict scoping to prevent cross-user leakage).

---

## 2. MongoDB Collections & Schemas

The database contains two primary collections: `events` and `users`.

### 2.1. `events` Collection

Stores normalized event documents extracted by scrapers (Meetup, Devpost, etc.).

| Field | Type | Required | Description |
|---|---|---|---|
| `_id` | `ObjectId` | Yes | MongoDB primary key |
| `title` | `String` | Yes | Title of the event |
| `event_url` | `String` | Yes | Canonical source URL |
| `date_time` | `String` (ISO 8601 UTC) | Yes | Scheduled event start time |
| `organizer` | `String` | Yes | Host organization or community name |
| `source` | `String` | Yes | Source platform (e.g., `"meetup"`) |
| `mode_location` | `String` | Yes | Location string (e.g., `"Online"`, `"Offline - Hyderabad"`) |
| `city` | `String` \| `null` | No | Extracted city |
| `country` | `String` \| `null` | No | Extracted country |
| `poster_image_url`| `String` \| `null` | No | Event banner or cover image |
| `description` | `String` \| `null` | No | Full markdown or text event description |
| `is_free` | `Boolean` | Yes | Whether the event is free to attend |
| `price_amount` | `Number` \| `null` | No | Ticket cost if paid |
| `price_currency`| `String` \| `null` | No | Currency ISO code (e.g., `"USD"`, `"INR"`) |
| `source_event_id`| `String` | Yes | Platform-specific ID for deduplication |
| `registration_url`| `String` \| `null` | No | External registration or RSVP link |
| `is_technical` | `Boolean` | Yes | Classifier flag indicating technical content |
| `categories` | `Array[String]` | Yes | Topics/tags (e.g., `["AI / ML", "Cloud"]`) |
| `scraped_at` | `String` (ISO 8601 UTC) | Yes | Extraction timestamp |
| `created_at` | `String` (ISO 8601 UTC) | Yes | First insertion timestamp |

#### Indexes for `events`
* `{"source": 1, "source_event_id": 1}` — Unique compound index for idempotent scraping.
* `{"date_time": 1}` — Ascending index for querying upcoming events and filtering expired events.

---

### 2.2. `users` Collection

Stores registered user accounts, authentication credentials, personalization preferences, and saved event identifiers.

| Field | Type | Required | Description |
|---|---|---|---|
| `_id` | `ObjectId` | Yes | MongoDB primary key |
| `email` | `String` | Yes | Normalized lowercase unique email |
| `password_hash` | `String` | Yes | Bcrypt one-way password hash (never plain text) |
| `interests` | `Array[String]` | Yes | Selected technical topics (e.g., `["AI / ML", "Cloud"]`) |
| `skills` | `Array[String]` | Yes | User technical skills & tools (e.g., `["Python", "FastAPI"]`) |
| `preferred_event_types` | `Array[String]` | Yes | Preferred event types (e.g., `["Hackathon", "Workshop"]`) |
| `preferred_modes` | `Array[String]` | Yes | Preferred attendance modes (e.g., `["Online", "Hybrid"]`) |
| `saved_event_ids` | `Array[String]` | Yes | Array of event MongoDB `_id` strings bookmarked by this user |
| `created_at` | `String` (ISO 8601 UTC) | Yes | Account creation timestamp |

#### Indexes for `users`
* `{"email": 1}` — Unique index (`idx_users_email_unique`) ensuring no duplicate accounts.
* `{"saved_event_ids": 1}` — Multikey index (`idx_users_saved_event_ids`) for efficient lookup of saved items.

---

## 3. Design Decisions & Rationale

### 3.1. Embedded `saved_event_ids` vs. Separate Junction Collection

**Decision:** We store `saved_event_ids: List[str]` directly in the `users` document rather than creating a separate `saved_events` junction collection.

**Rationale:**
1. **Single-Document Atomicity & Performance:** Fetching a user's profile and checking whether an event is saved requires only a single read from the `users` collection.
2. **Atomic Idempotency:** MongoDB's `$addToSet` operator atomically appends an event ID only if it does not already exist, preventing race conditions and duplicate entries without needing explicit transactions or unique constraint errors. Unsaving is equally atomic with `$pull`.
3. **Scale Alignment:** Most users bookmark dozens or hundreds of events, not millions. An array of 1,000 ObjectId strings occupies under 25 KB, well below MongoDB's 16 MB document limit.
4. **Future Expansion:** If future requirements demand per-save metadata (e.g., personal notes, custom reminders, or save timestamps), this can cleanly migrate to embedded subdocuments `saved_events: [{event_id, saved_at, notes}]` without breaking the schema contract.

### 3.2. Password Storage & Authentication Architecture

**Decision:** Passwords are never stored in plain text. Hashing is performed using `bcrypt` via `passlib.context.CryptContext`.
* **Salt & Work Factor:** Automatically handled by bcrypt with industry-standard cost parameters.
* **Enumeration Defense:** Login failures return a generic `401 Unauthorized: "Invalid email or password"` rather than revealing whether an email exists in the database.
* **Leak Prevention:** The `password_hash` field is explicitly excluded from all API response models and Pydantic schemas (`UserPublic`).
* **Session Management:** Stateless JSON Web Tokens (JWT) signed using HMAC-SHA256 (`HS256`) with configurable expiration (`JWT_EXPIRE_DAYS=7`).

### 3.3. Strict User Isolation

Every personalized operation (`GET /me/preferences`, `PUT /me/preferences`, `POST /events/{id}/save`, `DELETE /events/{id}/save`, `GET /events/saved`) derives the user identity exclusively from the validated JWT Bearer token:
```python
current_user: Dict[str, Any] = Depends(get_current_user)
```
* Clients **cannot** pass a `user_id` query parameter or body attribute to access or modify data belonging to other accounts.
* User A saving an event modifies only User A's document in the `users` collection. User B's saved list remains completely untouched.

---

## 4. API Endpoints Specification

### 4.1. Authentication
* **`POST /auth/register`**  
  * Request: `{"email": "user@example.com", "password": "SecurePassword123"}`  
  * Response: `{"access_token": "...", "token_type": "bearer", "user": {...}}` (HTTP 201)  
  * Errors: HTTP 400 if email is already registered, HTTP 422 if validation fails.

* **`POST /auth/login`**  
  * Request: `{"email": "user@example.com", "password": "SecurePassword123"}`  
  * Response: `{"access_token": "...", "token_type": "bearer", "user": {...}}` (HTTP 200)  
  * Errors: HTTP 401 if credentials do not match.

* **`GET /auth/me`**  
  * Headers: `Authorization: Bearer <token>`  
  * Response: Public user profile without `password_hash` (HTTP 200)

### 4.2. Preferences
* **`GET /me/preferences`**  
  * Headers: `Authorization: Bearer <token>`  
  * Response: `{"interests": [...], "skills": [...], "preferred_event_types": [...], "preferred_modes": [...]}`

* **`PUT /me/preferences`**  
  * Headers: `Authorization: Bearer <token>`  
  * Request Body: Partial or full preferences object.  
  * Validation: Options are validated against allowed domains (e.g., `VALID_INTERESTS`, `VALID_EVENT_TYPES`, `VALID_MODES`). Invalid items return HTTP 422.

### 4.3. Saved Events
* **`POST /events/{event_id}/save`**  
  * Headers: `Authorization: Bearer <token>`  
  * Response: `{"saved": true, "event_id": "<id>"}` (HTTP 200)  
  * Behavior: Idempotent `$addToSet`. Returns HTTP 404 if event does not exist in `events` collection.

* **`DELETE /events/{event_id}/save`**  
  * Headers: `Authorization: Bearer <token>`  
  * Response: `{"saved": false, "event_id": "<id>"}` (HTTP 200)  
  * Behavior: Idempotent `$pull`.

* **`GET /events/saved`**  
  * Headers: `Authorization: Bearer <token>`  
  * Response: List of full `Event` objects saved by the user (HTTP 200). Returns `[]` if no events are saved.

---

## 5. Security & Development Considerations

1. **Environment Variables:** All secrets (`JWT_SECRET_KEY`, `MONGODB_URI`) reside strictly in `.env` and are never committed to version control.
2. **CORS:** FastAPI CORS middleware is configured for local frontend origins (`http://localhost:3000`) and permits methods `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`.
3. **Frontend Token Storage:** Stored in browser `localStorage` for development simplicity; production deployments should transition to `httpOnly`, `Secure`, `SameSite` cookies to protect against XSS token extraction.
