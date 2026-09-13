# EventScout Chrome Extension (Manifest V3)

The **EventScout Clipper** is a Chrome extension built on **Manifest V3** that allows developers to discover, extract metadata from, and 1-click bookmark technical hackathons, workshops, conferences, and meetups while browsing the web.

---

## 🌟 Key Features

1. **Intelligent Event Detection**:
   - Analyzes Schema.org (`itemtype="https://schema.org/Event"`), JSON-LD, OpenGraph, and DOM microdata to extract event title, organizer, dates, location, and description.
2. **1-Click Bookmark**:
   - Saves detected opportunities directly to your EventScout MongoDB backend and user profile via `POST /events/extension-save`.
3. **Deep Link to EventScout**:
   - Fast shortcut to jump directly into the full EventScout discovery dashboard.
4. **Manifest V3 Architecture**:
   - Modern service worker background execution (`background.js`), non-blocking content script (`content.js`), and isolated local storage (`chrome.storage.local`).

---

## 🚀 How to Install & Test Locally

1. Open Google Chrome (or Chromium-based browsers like Brave, Edge).
2. Navigate to `chrome://extensions/`.
3. In the top-right corner, toggle **Developer mode** to **ON**.
4. Click **Load unpacked** in the top-left corner.
5. Select this folder:
   ```text
   <path-to-project>/EventScout/extension
   ```
6. The **EventScout — Opportunity Discovery & Clipper** extension icon will now appear in your browser toolbar!

---

## 🧪 Quick Test

1. Visit any technical hackathon or event page (e.g. `https://devpost.com/hackathons` or an event detail page).
2. Click the EventScout extension icon in the toolbar.
3. The popup will automatically scan the page, show detected details (Title, Organizer, Mode, Date), and present the **Save to EventScout** button.
4. Click **Save to EventScout** to bookmark the event into your live EventScout platform.
