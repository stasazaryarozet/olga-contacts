#!/usr/bin/env python3
"""
Calendar Pipeline: ICS file → Events → Participants → Graph Relations
Извлекает связи между контактами на основе совместных событий из календаря.
Работает с экспортированными ICS файлами (Google Calendar, Apple Calendar, Outlook).
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import json
import re

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from graph_db import GraphDB
from utils import log


def install_icalendar():
    """Install icalendar library if not available."""
    try:
        import icalendar
    except ImportError:
        log("📦 Installing icalendar...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "icalendar"])


def parse_ics_file(ics_file):
    """Parse ICS calendar file."""
    import icalendar
    
    log(f"📅 Parsing ICS file: {ics_file}")
    
    with open(ics_file, 'rb') as f:
        cal = icalendar.Calendar.from_ical(f.read())
    
    events = []
    
    for component in cal.walk():
        if component.name == "VEVENT":
            event = {}
            
            # Extract event data
            event['id'] = str(component.get('uid', ''))
            event['summary'] = str(component.get('summary', 'Untitled Event'))
            
            # Start time
            dtstart = component.get('dtstart')
            if dtstart:
                event['start'] = dtstart.dt.isoformat() if hasattr(dtstart.dt, 'isoformat') else str(dtstart.dt)
            else:
                event['start'] = None
            
            # Attendees
            attendees_list = component.get('attendee', [])
            if not isinstance(attendees_list, list):
                attendees_list = [attendees_list]
            
            event['attendees'] = []
            for attendee in attendees_list:
                # Extract email from "mailto:email@domain.com"
                email = str(attendee)
                if email.startswith('mailto:'):
                    email = email[7:]
                
                # Get CN (common name) parameter
                cn = attendee.params.get('CN', email) if hasattr(attendee, 'params') else email
                
                event['attendees'].append({
                    'email': email,
                    'displayName': cn
                })
            
            # Organizer
            organizer = component.get('organizer')
            if organizer:
                email = str(organizer)
                if email.startswith('mailto:'):
                    email = email[7:]
                
                cn = organizer.params.get('CN', email) if hasattr(organizer, 'params') else email
                
                event['organizer'] = {
                    'email': email,
                    'displayName': cn
                }
            
            events.append(event)
    
    log(f"✅ Parsed {len(events)} events")
    return events


def extract_attendees(event):
    """Extract attendees from event."""
    attendees = []
    
    # Get attendees list
    for attendee in event.get('attendees', []):
        email = attendee.get('email')
        if not email:
            continue
        
        name = attendee.get('displayName', email)
        
        attendees.append({
            'email': email,
            'name': name
        })
    
    # Also get organizer
    organizer = event.get('organizer', {})
    if organizer and organizer.get('email'):
        attendees.append({
            'email': organizer['email'],
            'name': organizer.get('displayName', organizer['email']),
            'is_organizer': True
        })
    
    return attendees


def process_calendar_events(events, db):
    """Process calendar events and create graph relations."""
    log(f"\n🔗 Processing events to create relations...")
    
    total_relations = 0
    processed_events = 0
    
    for event in events:
        event_id = event.get('id')
        event_name = event.get('summary', 'Untitled Event')
        start = event.get('start')  # Already a string from parse_ics_file
        
        # Skip events without names
        if not event_name or event_name == 'Untitled Event':
            continue
        
        # Extract attendees
        attendees = extract_attendees(event)
        
        # Skip events with < 2 attendees (no relations to create)
        if len(attendees) < 2:
            continue
        
        log(f"\n   Event: {event_name} ({start})")
        log(f"   Attendees: {len(attendees)}")
        
        # Create Event node
        event_node_id = f"event:{event_id}"
        db.conn.execute("""
            INSERT OR IGNORE INTO nodes (canonical_id, name, type, metadata, first_seen)
            VALUES (?, ?, 'Event', ?, datetime())
        """, (event_node_id, event_name, json.dumps({'date': start, 'id': event_id})))
        
        # Create Person nodes for attendees
        for attendee in attendees:
            person_id = f"email:{attendee['email']}"
            
            db.conn.execute("""
                INSERT OR IGNORE INTO nodes (canonical_id, name, type, metadata, first_seen)
                VALUES (?, ?, 'Person', ?, datetime())
            """, (person_id, attendee['name'], json.dumps({'email': attendee['email']})))
            
            # Create participated_in relation
            fact_id = f"{person_id}:participated_in:{event_node_id}"
            
            db.conn.execute("""
                INSERT OR IGNORE INTO facts 
                (fact_id, relation_type, subject_id, object_id, confidence, context, created_at)
                VALUES (?, 'participated_in', ?, ?, 0.95, ?, datetime())
            """, (fact_id, person_id, event_node_id, f"Attended '{event_name}' on {start}"))
            
            total_relations += 1
        
        # Create co-attended relations (N×N)
        for i, attendee1 in enumerate(attendees):
            for attendee2 in attendees[i+1:]:
                person1_id = f"email:{attendee1['email']}"
                person2_id = f"email:{attendee2['email']}"
                
                fact_id = f"{person1_id}:co_attended:{person2_id}:{event_id}"
                
                db.conn.execute("""
                    INSERT OR IGNORE INTO facts 
                    (fact_id, relation_type, subject_id, object_id, confidence, context, created_at)
                    VALUES (?, 'co_attended', ?, ?, 0.90, ?, datetime())
                """, (fact_id, person1_id, person2_id, f"Both attended '{event_name}' on {start}"))
                
                total_relations += 1
        
        processed_events += 1
        
        # Add source
        source_url = f"gcal:event:{event_id}"
        db.conn.execute("""
            INSERT OR IGNORE INTO sources (url, authority, first_seen, last_processed)
            VALUES (?, 1.0, datetime(), datetime())
        """, (source_url,))
    
    db.conn.commit()
    
    log(f"\n✅ Processed {processed_events} events")
    log(f"   Created {total_relations} relations")
    
    return processed_events, total_relations


def main():
    """Main calendar pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import Calendar events from ICS file')
    parser.add_argument('ics_file', help='Path to ICS calendar file')
    
    args = parser.parse_args()
    
    if not os.path.exists(args.ics_file):
        log(f"❌ File not found: {args.ics_file}")
        return 1
    
    log("=" * 60)
    log("CALENDAR PIPELINE")
    log("=" * 60)
    
    # Install dependencies
    install_icalendar()
    
    # Parse ICS file
    events = parse_ics_file(args.ics_file)
    
    if not events:
        log("⚠️  No events found")
        return 0
    
    # Initialize graph DB
    db = GraphDB()
    
    # Process events
    processed, relations = process_calendar_events(events, db)
    
    # Show final stats
    log("\n" + "=" * 60)
    log("FINAL STATS")
    log("=" * 60)
    
    stats = db.get_stats()
    for key, val in stats.items():
        log(f"   {key}: {val}")
    
    db.close()
    
    log("\n✅ Calendar pipeline completed")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

