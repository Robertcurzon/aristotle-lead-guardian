# Lead CSV Data Schema

Aristotle Lead Guardian accepts a plain CSV file. Column names are normalized to snake_case, so `Lead ID`, `lead id`, and `lead_id` all resolve to `lead_id`.

## Required Columns

| Column | Type | Description |
|---|---|---|
| `lead_id` | string | Unique lead identifier. |
| `created_at` | date | Lead creation date. |
| `name` | string | Contact name. |
| `email` | string | Contact email. |
| `phone` | string | Contact phone number. |
| `source` | string | Acquisition source or channel. |
| `status` | string | Suggested values: New, Contacted, Nurture, Appointment, Won, Lost. |
| `budget` | number | Estimated deal size, purchase budget, or customer value. |
| `intent` | string | Suggested values: Ready, High, Medium, Low, Researching. |
| `timeline_days` | number | Estimated days until purchase or decision. |
| `last_contacted_at` | date | Date of last human or automated touch. Blank is allowed. |
| `engagement_score` | number | 0-100 behavioral score from form depth, clicks, replies, or CRM activity. |
| `notes` | string | Context used by the follow-up agent. |

## Optional Columns

| Column | Description |
|---|---|
| `assigned_to` | Owner or sales rep. |
| `region` | Territory, market, or location. |
| `service_type` | Buyer, seller, repair, consultation, quote, etc. |
| `preferred_channel` | Phone, SMS, Email, or other channel. |

## Scoring Signals

The scoring engine combines:

- Lead recency
- Declared intent
- Behavioral engagement
- Budget or estimated deal value
- Decision timeline
- Current status
- Follow-up latency and SLA risk

