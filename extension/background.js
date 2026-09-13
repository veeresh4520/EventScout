/**
 * EventScout Browser Extension - Background Service Worker (Manifest V3)
 * Manages API calls to EventScout backend and token storage.
 */

const API_BASE_URL = 'http://localhost:8000';

chrome.runtime.onInstalled.addListener(() => {
  console.log('EventScout Extension installed successfully.');
  // Set up daily alarm
  chrome.alarms.create('dailyScoutFetch', {
    periodInMinutes: 1440 // 24 hours
  });
});

chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === 'dailyScoutFetch') {
    fetchDailyEventsAndNotify();
  }
});

async function fetchDailyEventsAndNotify() {
  try {
    const storage = await chrome.storage.local.get(['eventscout_token']);
    const token = storage.eventscout_token;
    if (!token) {
      console.log('No token found, skipping daily notification.');
      return;
    }

    const response = await fetch(`${API_BASE_URL}/events?limit=5&sort_by=score`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`
      }
    });

    if (response.ok) {
      const data = await response.json();
      if (data.events && data.events.length > 0) {
        chrome.notifications.create({
          type: 'basic',
          iconUrl: 'icon.png', // Assuming we add one, or generic
          title: 'New Top Events on EventScout!',
          message: `Found ${data.events.length} new events that match your profile. Check them out!`,
          priority: 2
        });
      }
    }
  } catch (error) {
    console.error('Failed to fetch daily events:', error);
  }
}

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'SAVE_EVENT') {
    handleSaveEvent(request.payload)
      .then((res) => sendResponse({ success: true, data: res }))
      .catch((err) => sendResponse({ success: false, error: err.message }));
    return true; // Keep message channel open for async response
  }

  if (request.action === 'SET_AUTH_TOKEN') {
    chrome.storage.local.set({ eventscout_token: request.token }, () => {
      sendResponse({ success: true });
    });
    return true;
  }
});

async function handleSaveEvent(eventData) {
  // Retrieve token if stored
  const storage = await chrome.storage.local.get(['eventscout_token']);
  const token = storage.eventscout_token;

  const headers = {
    'Content-Type': 'application/json',
  };
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const response = await fetch(`${API_BASE_URL}/events/extension-save`, {
    method: 'POST',
    headers: headers,
    body: JSON.stringify(eventData),
  });

  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`Failed to save event (${response.status}): ${errorText}`);
  }

  return await response.json();
}
