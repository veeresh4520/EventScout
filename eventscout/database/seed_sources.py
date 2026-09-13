"""
Predefined Source Registry Seeder for EventScout.
Populates the 15 official sources into MongoDB if not already present.
Meetup is seeded as ENABLED (backed by the verified GraphQL interceptor),
while others are seeded as READY_FOR_REVIEW or PENDING with their verified base & event listing URLs.
"""
import logging
from typing import Any, Dict, List
from eventscout.database.source_db import SourceDatabase

logger = logging.getLogger("SeedSources")

PREDEFINED_SOURCES: List[Dict[str, Any]] = [
    {
        "name": "Devfolio",
        "base_url": "https://devfolio.co/",
        "event_list_url": "https://devfolio.co/hackathons",
        "source_type": "hackathon_platform",
        "status": "READY_FOR_REVIEW",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://devfolio.co/hackathons",
            "container_selector": "div[class*='HackathonCard'], div[class*='hackathon-card'], a[href*='devfolio.co']",
            "fields": {
                "title": {"selector": "h3, h4, [class*='title']", "type": "text"},
                "event_url": {"selector": "a", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "[class*='date'], time", "type": "text"},
                "description": {"selector": "p, [class*='desc']", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "Unstop",
        "base_url": "https://unstop.com/",
        "event_list_url": "https://unstop.com/hackathons",
        "source_type": "hackathon_platform",
        "status": "READY_FOR_REVIEW",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://unstop.com/hackathons",
            "container_selector": "a.item[href*='/hackathons/'], a[href*='/hackathons/'], a[href*='/competitions/']",
            "wait_selector": "a[href*='/hackathons/']",
            "fields": {
                "title": {"selector": "h3, h4, [class*='title'], strong, img[alt]", "type": "text"},
                "event_url": {"selector": "self", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "[class*='date'], [class*='deadline'], span", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "Hack2Skill",
        "base_url": "https://hack2skill.com/",
        "event_list_url": "https://hack2skill.com/",
        "source_type": "hackathon_platform",
        "status": "ENABLED",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://hack2skill.com/",
            "container_selector": "a[href*='hack2skill.com/event/'], a[href*='vision.hack2skill.com/event/'], a[href*='/hack/']",
            "fields": {
                "title": {"selector": "self", "type": "text"},
                "event_url": {"selector": "self", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "self", "type": "text"},
                "location": {"selector": "self", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "Meetup",
        "base_url": "https://www.meetup.com/",
        "event_list_url": "https://www.meetup.com/find/?categoryId=546&source=EVENTS",
        "source_type": "event_platform",
        "status": "ENABLED",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://www.meetup.com/find/?categoryId=546&source=EVENTS",
            "adapter": "meetup_graphql_interceptor",
            "category_id": 546,
        },
    },
    {
        "name": "Google Developer Groups",
        "base_url": "https://gdg.community.dev/",
        "event_list_url": "https://gdg.community.dev/events/#/list",
        "source_type": "community",
        "status": "ENABLED",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://gdg.community.dev/events/#/list",
            "container_selector": "a[href*='/events/details/'], div[class*='event-card']",
            "wait_selector": "a[href*='/events/details/']",
            "fields": {
                "title": {"selector": "h3, h4, [class*='title'], strong", "type": "text"},
                "event_url": {"selector": "self", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "[class*='date'], span, div", "type": "text"},
                "mode_location": {"selector": "[class*='location'], span", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "Microsoft Reactor",
        "base_url": "https://developer.microsoft.com/en-us/reactor/",
        "event_list_url": "https://developer.microsoft.com/en-us/reactor/",
        "source_type": "community",
        "status": "ENABLED",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://developer.microsoft.com/en-us/reactor/",
            "container_selector": "a[href*='/reactor/events/']:not([href*='#'])",
            "fields": {
                "title": {"selector": "self", "type": "text"},
                "event_url": {"selector": "self", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "self", "type": "text"},
                "location": {"selector": "self", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "T-Hub",
        "base_url": "https://t-hub.co/",
        "event_list_url": "https://t-hub.co/events-calendar",
        "source_type": "community",
        "status": "ENABLED",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://t-hub.co/events-calendar",
            "container_selector": "a[href*='program'], a[href*='hackathon'], div[class*='event'], div[class*='card']",
            "fields": {
                "title": {"selector": "h2, h3, h4, a, self", "type": "text"},
                "event_url": {"selector": "self, a", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "p, self", "type": "text"},
                "location": {"selector": "self", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "AWS Community",
        "base_url": "https://community.aws/",
        "event_list_url": "https://builder.aws.com/connect/events",
        "source_type": "community",
        "status": "ENABLED",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://builder.aws.com/connect/events",
            "container_selector": "a[href*='/connect/'], a[href*='/content/'], div[class*='card']",
            "fields": {
                "title": {"selector": "h3, h4, span, self", "type": "text"},
                "event_url": {"selector": "self, a", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "p, self", "type": "text"},
                "location": {"selector": "self", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "MLH",
        "base_url": "https://mlh.io/",
        "event_list_url": "https://www.mlh.com/seasons/2026/events",
        "source_type": "hackathon_platform",
        "status": "READY_FOR_REVIEW",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://www.mlh.com/seasons/2026/events",
            "container_selector": "a[itemtype*='Event'], a.group, div.event-wrapper",
            "wait_selector": "a[itemtype*='Event']",
            "fields": {
                "title": {"selector": "h3, [class*='event-name']", "type": "text"},
                "event_url": {"selector": "self", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "p, [class*='date']", "type": "text"},
                "location": {"selector": "div, [class*='location']", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "HackerEarth",
        "base_url": "https://www.hackerearth.com/",
        "event_list_url": "https://www.hackerearth.com/challenges/",
        "source_type": "hackathon_platform",
        "status": "ENABLED",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://www.hackerearth.com/challenges/",
            "container_selector": "a[href*='/community/challenges/'], a[href*='/challenges/hackathon/'], a[href*='/challenges/competitive/']",
            "fields": {
                "title": {"selector": "self", "type": "text"},
                "event_url": {"selector": "self", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "self", "type": "text"},
                "location": {"selector": "self", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "Devpost",
        "base_url": "https://devpost.com/",
        "event_list_url": "https://devpost.com/hackathons",
        "source_type": "hackathon_platform",
        "status": "READY_FOR_REVIEW",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://devpost.com/hackathons",
            "container_selector": "div.hackathon-tile, article[class*='challenge']",
            "fields": {
                "title": {"selector": "h3, h2, [class*='title']", "type": "text"},
                "event_url": {"selector": "a[href*='devpost.com']", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "[class*='date'], [class*='submission-period']", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
                "description": {"selector": "p", "type": "text"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "FOSS United",
        "base_url": "https://fossunited.org/",
        "event_list_url": "https://fossunited.org/events",
        "source_type": "community",
        "status": "READY_FOR_REVIEW",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://fossunited.org/events",
            "container_selector": "div[class*='event-card'], div[class*='card']",
            "fields": {
                "title": {"selector": "h3, h4, h2", "type": "text"},
                "event_url": {"selector": "a", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "[class*='date']", "type": "text"},
                "mode_location": {"selector": "[class*='city'], [class*='location']", "type": "text"},
            },
            "pagination": {"type": "scroll"},
        },
    },
    {
        "name": "IIIT Hyderabad",
        "base_url": "https://www.iiit.ac.in/",
        "event_list_url": "https://www.iiit.ac.in/events/",
        "source_type": "university",
        "status": "READY_FOR_REVIEW",
        "collection_strategy": "HTML",
        "configuration": {
            "target_url": "https://www.iiit.ac.in/events/",
            "container_selector": "div[class*='event'], li[class*='event']",
            "fields": {
                "title": {"selector": "h3, h4, a", "type": "text"},
                "event_url": {"selector": "a", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "[class*='date']", "type": "text"},
            },
        },
    },
    {
        "name": "IIT Hyderabad",
        "base_url": "https://www.iith.ac.in/",
        "event_list_url": "https://www.iith.ac.in/events/",
        "source_type": "university",
        "status": "READY_FOR_REVIEW",
        "collection_strategy": "HTML",
        "configuration": {
            "target_url": "https://www.iith.ac.in/events/",
            "container_selector": "div[class*='event'], article",
            "fields": {
                "title": {"selector": "h3, h4, a", "type": "text"},
                "event_url": {"selector": "a", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "[class*='date']", "type": "text"},
            },
        },
    },
    {
        "name": "Eventbrite",
        "base_url": "https://www.eventbrite.com/",
        "event_list_url": "https://www.eventbrite.com/d/online/science-and-tech--events/",
        "source_type": "event_platform",
        "status": "READY_FOR_REVIEW",
        "collection_strategy": "PLAYWRIGHT",
        "configuration": {
            "target_url": "https://www.eventbrite.com/d/online/science-and-tech--events/",
            "container_selector": "div[class*='event-card'], section.event-card-details, div.discover-horizontal-event-card",
            "wait_selector": "div[class*='event-card']",
            "fields": {
                "title": {"selector": "h3, [class*='title']", "type": "text"},
                "event_url": {"selector": "a[href*='/e/']", "type": "attribute", "attribute": "href"},
                "date_time": {"selector": "p[class*='date'], [class*='date']", "type": "text"},
                "organizer": {"selector": "p[class*='organizer']", "type": "text"},
                "poster_image_url": {"selector": "img", "type": "attribute", "attribute": "src"},
            },
            "pagination": {"type": "scroll"},
        },
    },
]


def seed_predefined_sources(source_db: SourceDatabase = None) -> int:
    """
    Seeds all 15 predefined sources into the MongoDB sources collection if they don't already exist.
    Returns the count of new sources seeded.
    """
    db = source_db or SourceDatabase()
    seeded_count = 0

    for source in PREDEFINED_SOURCES:
        url = source["base_url"]
        existing = db.find_duplicate_source(url)
        if not existing:
            doc = db.create_source(
                url=source["base_url"],
                name=source["name"],
                status=source["status"],
                source_type=source.get("source_type", "event_platform"),
                event_list_url=source.get("event_list_url"),
                collection_strategy=source.get("collection_strategy", "PLAYWRIGHT"),
                configuration=source.get("configuration", {}),
                created_by="system",
            )
            seeded_count += 1
            logger.info("Seeded predefined source: %s (%s)", source["name"], doc["id"])
        else:
            # If it already exists, ensure base_url, event_list_url, and name are updated if missing
            updates = {}
            if not existing.get("event_list_url") and source.get("event_list_url"):
                updates["event_list_url"] = source["event_list_url"]
            if not existing.get("source_type") and source.get("source_type"):
                updates["source_type"] = source["source_type"]
            if updates:
                db.update_source(existing["id"], updates)

    logger.info("Predefined source seeding check finished. %d new source(s) created.", seeded_count)
    return seeded_count


if __name__ == "__main__":
    count = seed_predefined_sources()
    print(f"Seeded {count} sources.")
