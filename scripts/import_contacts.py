#!/usr/bin/env python3
"""
VCard Parser для импорта контактов в граф.
Поддерживает: Google Contacts (CSV), Outlook (CSV), Apple Contacts (VCF)
"""

import sys
import csv
import sqlite3
from pathlib import Path

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from graph_db import GraphDB
from utils import log


def parse_vcard(vcf_file: str) -> list:
    """Parse VCard (.vcf) file."""
    try:
        import vobject
    except ImportError:
        print("Installing vobject...")
        import subprocess
        subprocess.check_call([sys.executable, "-m", "pip", "install", "vobject"])
        import vobject
    
    contacts = []
    
    with open(vcf_file, 'r', encoding='utf-8') as f:
        for vcard in vobject.readComponents(f):
            contact = {}
            
            # Name
            if hasattr(vcard, 'fn'):
                contact['name'] = vcard.fn.value
            
            # Organization
            if hasattr(vcard, 'org'):
                contact['organization'] = vcard.org.value[0] if vcard.org.value else None
            
            # Email
            if hasattr(vcard, 'email'):
                contact['email'] = vcard.email.value
            
            # Phone
            if hasattr(vcard, 'tel'):
                contact['phone'] = vcard.tel.value
            
            # Title
            if hasattr(vcard, 'title'):
                contact['title'] = vcard.title.value
            
            if contact.get('name'):
                contacts.append(contact)
    
    return contacts


def parse_google_csv(csv_file: str) -> list:
    """Parse Google Contacts CSV export."""
    contacts = []
    
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            contact = {}
            
            # Google Contacts CSV format - try multiple column names
            first_name = row.get('First Name', '').strip()
            middle_name = row.get('Middle Name', '').strip()
            last_name = row.get('Last Name', '').strip()
            
            # Construct full name
            name_parts = [first_name, middle_name, last_name]
            name = ' '.join([p for p in name_parts if p])
            
            # Fallback to 'Name' column
            if not name:
                name = row.get('Name', '').strip()
            
            email = row.get('E-mail 1 - Value', '').strip() or row.get('Email', '').strip()
            org = row.get('Organization Name', '').strip() or row.get('Organization 1 - Name', '').strip() or row.get('Company', '').strip()
            title = row.get('Organization Title', '').strip() or row.get('Organization 1 - Title', '').strip() or row.get('Job Title', '').strip()
            phone = row.get('Phone 1 - Value', '').strip()
            
            if name:
                contact['name'] = name
                if email:
                    contact['email'] = email
                if org:
                    contact['organization'] = org
                if title:
                    contact['title'] = title
                if phone:
                    contact['phone'] = phone
                
                contacts.append(contact)
    
    return contacts


def parse_outlook_csv(csv_file: str) -> list:
    """Parse Outlook CSV export."""
    contacts = []
    
    with open(csv_file, 'r', encoding='utf-8-sig') as f:  # Outlook uses BOM
        reader = csv.DictReader(f)
        
        for row in reader:
            contact = {}
            
            # Outlook CSV format
            first_name = row.get('First Name', '').strip()
            last_name = row.get('Last Name', '').strip()
            name = f"{first_name} {last_name}".strip()
            
            email = row.get('E-mail Address', '').strip()
            org = row.get('Company', '').strip()
            title = row.get('Job Title', '').strip()
            phone = row.get('Business Phone', '').strip()
            
            if name:
                contact['name'] = name
                if email:
                    contact['email'] = email
                if org:
                    contact['organization'] = org
                if title:
                    contact['title'] = title
                if phone:
                    contact['phone'] = phone
                
                contacts.append(contact)
    
    return contacts


def import_contacts_to_graph(contacts: list, db: GraphDB, source: str = "contacts"):
    """Import parsed contacts into graph database."""
    imported = 0
    
    for contact in contacts:
        try:
            name = contact['name']
            
            # Create Person node
            person_id = f"contact:{name.lower().replace(' ', '_')}"
            
            # If has email, use it as canonical ID
            if contact.get('email'):
                person_id = f"email:{contact['email']}"
            
            # Store as entity
            db.conn.execute("""
                INSERT OR IGNORE INTO nodes (canonical_id, name, type, metadata, first_seen)
                VALUES (?, ?, 'Person', ?, datetime())
            """, (person_id, name, str(contact)))
            
            # If has organization, create relation
            if contact.get('organization'):
                org_name = contact['organization']
                org_id = f"org:{org_name.lower().replace(' ', '_')}"
                
                # Create Organization node
                db.conn.execute("""
                    INSERT OR IGNORE INTO nodes (canonical_id, name, type, first_seen)
                    VALUES (?, ?, 'Organization', datetime())
                """, (org_id, org_name))
                
                # Create works_at relation
                fact_id = f"{person_id}:works_at:{org_id}"
                
                db.conn.execute("""
                    INSERT OR IGNORE INTO facts 
                    (fact_id, relation_type, subject_id, object_id, confidence, context, created_at)
                    VALUES (?, 'works_at', ?, ?, 0.90, ?, datetime())
                """, (fact_id, person_id, org_id, f"From contacts: {contact.get('title', 'N/A')}"))
                
                # Create claim
                db.conn.execute("""
                    INSERT OR IGNORE INTO sources (url, authority, first_seen, last_processed)
                    VALUES (?, 1.0, datetime(), datetime())
                """, (source,))
                
                db.conn.execute("""
                    INSERT OR IGNORE INTO claims (source_url, fact_id, confidence_llm)
                    VALUES (?, ?, 0.90)
                """, (source, fact_id))
            
            imported += 1
            
        except Exception as e:
            log(f"Error importing contact {contact.get('name')}: {e}")
    
    db.conn.commit()
    return imported


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Import contacts into graph')
    parser.add_argument('file', help='Path to contacts file (.vcf or .csv)')
    parser.add_argument('--format', choices=['vcf', 'google', 'outlook', 'auto'], 
                       default='auto', help='File format (auto-detect by extension)')
    
    args = parser.parse_args()
    
    file_path = Path(args.file)
    
    if not file_path.exists():
        print(f"❌ File not found: {file_path}")
        return 1
    
    log(f"📥 Importing contacts from: {file_path}")
    
    # Auto-detect format
    if args.format == 'auto':
        if file_path.suffix.lower() == '.vcf':
            args.format = 'vcf'
        elif file_path.suffix.lower() == '.csv':
            # Try to detect CSV type by headers
            with open(file_path, 'r', encoding='utf-8') as f:
                first_line = f.readline()
                if 'E-mail 1 - Value' in first_line or 'Organization 1 - Name' in first_line:
                    args.format = 'google'
                else:
                    args.format = 'outlook'
        else:
            print(f"❌ Unknown file format: {file_path.suffix}")
            return 1
    
    log(f"   Format detected: {args.format}")
    
    # Parse contacts
    if args.format == 'vcf':
        contacts = parse_vcard(str(file_path))
    elif args.format == 'google':
        contacts = parse_google_csv(str(file_path))
    elif args.format == 'outlook':
        contacts = parse_outlook_csv(str(file_path))
    
    log(f"   Parsed {len(contacts)} contacts")
    
    # Import to graph
    db = GraphDB()
    imported = import_contacts_to_graph(contacts, db, source=f"file://{file_path}")
    db.close()
    
    log(f"✅ Imported {imported}/{len(contacts)} contacts to graph")
    
    # Show stats
    db = GraphDB()
    stats = db.get_stats()
    log(f"\n📈 Updated Database Stats:")
    for key, val in stats.items():
        log(f"   {key}: {val}")
    db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

