# EventScout — Ranking & Prioritization Architecture

A common failure mode of event discovery platforms is displaying events purely in order of scrape recency (`latest scraped event = top`). This buries high-value opportunities under casual local meetups.

EventScout uses an **intelligent multi-signal ranking engine** that ensures top-tier tech leader workshops, premier institute hackathons, and urgent personalized opportunities appear near the top while keeping smaller community events easily accessible.

---

## 1. Multi-Signal Composite Formula

For any event $E$ and user $U$, the final score is calculated as:

$$\text{Final Score} = w_{\text{org}} \cdot S_{\text{org}} + w_{\text{quality}} \cdot S_{\text{quality}} + w_{\text{user}} \cdot S_{\text{user}} + w_{\text{urgency}} \cdot S_{\text{urgency}}$$

Where weights are balanced to reward excellence without drowning out smaller organizers:

| Signal | Weight | Description |
|---|---|---|
| **$S_{\text{org}}$ (Organization Reputation)** | **35%** | Evaluates the host reputation tier and alias verification. |
| **$S_{\text{quality}}$ (Event Quality)** | **25%** | Rewards format (hackathon, workshop, conference) & technical depth. |
| **$S_{\text{user}}$ (Personalization)** | **25%** | Matches user's declared interests, skills, and mode preferences. |
| **$S_{\text{urgency}}$ (Deadline Urgency)** | **15%** | Prioritizes events closing within 48 hours or happening this week. |

---

## 2. Organization Reputation Registry (`organization_registry.py`)

Instead of fragile string matches like `if "Google" in organizer: score += 100`, EventScout maintains an extensible registry mapping normalized aliases to canonical organizations and reputation tiers:

### Host Tiers & Base Scores:
- **`TIER_1_COMPANY` (0.95 - 0.99)**: Google, Microsoft, AWS, Meta, Apple, NVIDIA, OpenAI, GitHub, IBM, Oracle, Intel, Cisco, Salesforce, Adobe.
- **`TOP_UNIVERSITY` (0.90 - 0.99)**: IIT Hyderabad, IIT Bombay, IIT Delhi, IIT Madras, IIIT Hyderabad, BITS Pilani, IISc Bangalore, Stanford, MIT, CMU.
- **`MAJOR_DEVELOPER_COMMUNITY` (0.87 - 0.93)**: MLH, Devfolio, Devpost, Unstop, CNCF, Linux Foundation, FOSS United, Python Software Foundation.
- **`TIER_2_COMPANY` (0.82 - 0.88)**: Databricks, Snowflake, MongoDB, Stripe, Uber, Postman, Docker.
- **`ESTABLISHED_ORGANIZATION` (0.78 - 0.88)**: T-Hub, Telangana AI Mission, NASSCOM.
- **`COLLEGE` (0.70)**: Recognized engineering and degree colleges.
- **`COMMUNITY` (0.60)**: Local meetups, chapters, clubs.
- **`INDIVIDUAL` (0.45)**: Independent creators and community organizers.
- **`UNKNOWN` (0.40)**: Unclassified organizers.

### Alias Resolution:
Organizations with multiple subdivisions (e.g. `Microsoft Reactor`, `Microsoft Foundry`, `Microsoft Developer`, `MS Reactor`) automatically resolve to the canonical `Microsoft` profile.

---

## 3. Preservation of Community & Smaller Events

The ranking algorithm is designed to ensure community and individual events are **never completely buried**:
- Baseline scores ensure community events remain discoverable in the "All Opportunities" view.
- User interest matches can elevate a local Python or Rust meetup above a generic company announcement.
- The UI separates **Top Picks** from the complete chronological or filtered opportunity feed.

---

## 4. Transparent Explainability ("Why Recommended?")

To build trust and give transparency without exposing internal floating-point numbers, EventScout generates clean, human-readable explanations displayed via the `✨ Why recommended?` toggle on each card:

- `✓ Hosted by premier tech leader Amazon Web Services`
- `✓ Matches your AI and Python interests`
- `✓ High-impact hands-on hackathon`
- `✓ Free registration`
- `✓ Happening in 3 days`
