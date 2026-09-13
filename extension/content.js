/**
 * EventScout Browser Extension - Content Script (Manifest V3)
 * Analyzes webpage DOM, JSON-LD microdata, and OpenGraph tags to detect
 * technical hackathons, workshops, and developer conferences.
 */

(function () {
  function extractJsonLdEvent() {
    try {
      const scripts = document.querySelectorAll('script[type="application/ld+json"]');
      for (const script of scripts) {
        let data;
        try {
          data = JSON.parse(script.innerText);
        } catch {
          continue;
        }

        const items = Array.isArray(data) ? data : [data];
        for (const item of items) {
          if (
            item['@type'] === 'Event' ||
            item['@type'] === 'EducationEvent' ||
            item['@type'] === 'Hackathon' ||
            (Array.isArray(item['@type']) && item['@type'].includes('Event'))
          ) {
            let organizer = 'Community Organizer';
            if (item.organizer) {
              organizer = typeof item.organizer === 'string' ? item.organizer : (item.organizer.name || 'Community Organizer');
            }

            let location = 'Online';
            if (item.location) {
              if (typeof item.location === 'string') {
                location = item.location;
              } else if (item.location.name || item.location.address) {
                location = item.location.name || item.location.address.addressLocality || 'In-Person';
              }
            }

            return {
              title: item.name || document.title,
              date_time: item.startDate || new Date().toISOString(),
              organizer: organizer,
              description: item.description || '',
              mode_location: location,
              event_url: item.url || window.location.href,
              is_free: item.isAccessibleForFree !== false,
              categories: ['Technical Event'],
              confidence: 0.95,
            };
          }
        }
      }
    } catch (e) {
      console.warn('EventScout: Error parsing JSON-LD', e);
    }
    return null;
  }

  function extractMetaEvent() {
    const getMeta = (prop) => {
      const tag = document.querySelector(`meta[property="${prop}"], meta[name="${prop}"]`);
      return tag ? tag.getAttribute('content') : null;
    };

    const title = getMeta('og:title') || getMeta('twitter:title') || document.title;
    const description = getMeta('og:description') || getMeta('twitter:description') || '';
    const siteName = getMeta('og:site_name') || window.location.hostname.replace('www.', '');
    const url = getMeta('og:url') || window.location.href;

    // Detect if page has event keywords
    const bodyText = (title + ' ' + description).toLowerCase();
    const eventKeywords = ['hackathon', 'workshop', 'conference', 'summit', 'bootcamp', 'meetup', 'webinar', 'devfest', 'codeathon'];
    const isLikelyEvent = eventKeywords.some((kw) => bodyText.includes(kw));

    let detectedType = 'Workshop';
    if (bodyText.includes('hackathon') || bodyText.includes('buildathon')) detectedType = 'Hackathon';
    else if (bodyText.includes('conference') || bodyText.includes('summit')) detectedType = 'Conference';
    else if (bodyText.includes('meetup')) detectedType = 'Meetup';

    let location = 'Online';
    if (bodyText.includes('in-person') || bodyText.includes('campus') || bodyText.includes('hyderabad') || bodyText.includes('bengaluru')) {
      location = 'In-Person';
    }

    return {
      title: title.replace(/ \| .*$/, '').replace(/ - .*$/, '').trim(),
      date_time: new Date(Date.now() + 86400000 * 3).toISOString(), // 3 days ahead placeholder if unparsed
      organizer: siteName,
      description: description.slice(0, 300),
      mode_location: location,
      event_url: url,
      is_free: !bodyText.includes('paid') && !bodyText.includes('ticket price'),
      categories: [detectedType],
      confidence: isLikelyEvent ? 0.8 : 0.4,
    };
  }

  function detectEvent() {
    const jsonLd = extractJsonLdEvent();
    if (jsonLd) return jsonLd;
    return extractMetaEvent();
  }

  // Listen for extraction requests from popup
  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'DETECT_EVENT') {
      const eventData = detectEvent();
      sendResponse({ status: 'ok', event: eventData });
    }
    return true;
  });
})();
