/**
 * EventScout Extension - Popup Logic
 */

document.addEventListener('DOMContentLoaded', async () => {
  const loadingView = document.getElementById('loadingView');
  const eventView = document.getElementById('eventView');
  const noEventView = document.getElementById('noEventView');
  const saveBtn = document.getElementById('saveBtn');
  const statusMessage = document.getElementById('statusMessage');

  let currentDetectedEvent = null;

  try {
    // Query active tab
    const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });

    if (!tab || !tab.id || tab.url.startsWith('chrome://') || tab.url.startsWith('edge://')) {
      showNoEvent();
      return;
    }

    // Send extraction request to content script
    chrome.tabs.sendMessage(tab.id, { action: 'DETECT_EVENT' }, (response) => {
      if (chrome.runtime.lastError || !response || !response.event) {
        // Fallback to basic tab info if content script did not return
        fallbackFromTab(tab);
        return;
      }

      displayEvent(response.event);
    });
  } catch (err) {
    console.error('Error scanning page:', err);
    showNoEvent();
  }

  function fallbackFromTab(tab) {
    if (!tab.title) {
      showNoEvent();
      return;
    }
    const detected = {
      title: tab.title.replace(/ \| .*$/, ''),
      date_time: new Date(Date.now() + 86400000 * 2).toISOString(),
      organizer: new URL(tab.url).hostname.replace('www.', ''),
      description: 'Discovered via EventScout Chrome Extension clipper.',
      mode_location: 'Online',
      event_url: tab.url,
      is_free: true,
      categories: ['Web Discovery'],
    };
    displayEvent(detected);
  }

  function displayEvent(event) {
    currentDetectedEvent = event;
    loadingView.classList.add('hidden');
    noEventView.classList.add('hidden');
    eventView.classList.remove('hidden');

    document.getElementById('eventTitle').textContent = event.title || 'Technical Event';
    document.getElementById('eventOrg').textContent = event.organizer || 'Organizer';
    document.getElementById('eventCategory').textContent = (event.categories && event.categories[0]) || 'Technical';
    document.getElementById('eventMode').textContent = event.mode_location || 'Online';
    document.getElementById('eventDesc').textContent = event.description || 'No description available.';

    if (event.date_time) {
      try {
        const d = new Date(event.date_time);
        document.getElementById('eventDate').textContent = d.toLocaleDateString(undefined, {
          month: 'short',
          day: 'numeric',
          year: 'numeric',
        });
      } catch {
        document.getElementById('eventDate').textContent = 'Upcoming';
      }
    }
  }

  function showNoEvent() {
    loadingView.classList.add('hidden');
    eventView.classList.add('hidden');
    noEventView.classList.remove('hidden');
  }

  // Handle Save Event
  saveBtn.addEventListener('click', () => {
    if (!currentDetectedEvent) return;

    saveBtn.disabled = true;
    saveBtn.innerHTML = 'Saving to EventScout...';
    statusMessage.classList.add('hidden');

    chrome.runtime.sendMessage(
      { action: 'SAVE_EVENT', payload: currentDetectedEvent },
      (response) => {
        saveBtn.disabled = false;
        saveBtn.innerHTML = '<span class="btn-icon">📥</span> Save to EventScout';

        if (response && response.success) {
          statusMessage.textContent = '✓ Saved to your EventScout dashboard!';
          statusMessage.className = 'status-message success';
          statusMessage.classList.remove('hidden');
        } else {
          statusMessage.textContent = (response && response.error) || 'Failed to save event. Ensure backend is running.';
          statusMessage.className = 'status-message error';
          statusMessage.classList.remove('hidden');
        }
      }
    );
  });
});
