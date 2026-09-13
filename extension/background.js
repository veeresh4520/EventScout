/**
 * EventScout Browser Extension - Background Service Worker (Manifest V3)
 * Manages API calls to EventScout backend and token storage.
 */

const API_BASE_URL = 'http://localhost:8000';

chrome.runtime.onInstalled.addListener(() => {
  console.log('EventScout Extension installed successfully.');
});

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
