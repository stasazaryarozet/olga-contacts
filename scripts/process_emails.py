#!/usr/bin/env python3
"""
Email Pipeline: IMAP → Parse → Groq IE → Graph
Автоматически извлекает контакты и связи из Gmail.
"""

import sys
import os
import imaplib
import email
from email.header import decode_header
from pathlib import Path
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time

sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))
from ie_pipeline import IEPipeline
from entity_resolution import resolve_entities
from graph_db import GraphDB
from utils import log


def decode_mime_header(header):
    """Decode MIME encoded header."""
    if header is None:
        return ""
    
    decoded = decode_header(header)
    result = []
    
    for part, encoding in decoded:
        if isinstance(part, bytes):
            try:
                result.append(part.decode(encoding or 'utf-8', errors='ignore'))
            except:
                result.append(part.decode('utf-8', errors='ignore'))
        else:
            result.append(str(part))
    
    return ''.join(result)


def extract_email_text(msg):
    """Extract plain text from email message."""
    text_parts = []
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            
            if content_type == 'text/plain':
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    text_parts.append(payload.decode(charset, errors='ignore'))
                except:
                    pass
            
            elif content_type == 'text/html' and not text_parts:
                # Use HTML only if no plain text found
                try:
                    payload = part.get_payload(decode=True)
                    charset = part.get_content_charset() or 'utf-8'
                    html = payload.decode(charset, errors='ignore')
                    soup = BeautifulSoup(html, 'html.parser')
                    text_parts.append(soup.get_text(separator='\n', strip=True))
                except:
                    pass
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            charset = msg.get_content_charset() or 'utf-8'
            text = payload.decode(charset, errors='ignore')
            
            if content_type == 'text/html':
                soup = BeautifulSoup(text, 'html.parser')
                text = soup.get_text(separator='\n', strip=True)
            
            text_parts.append(text)
        except:
            pass
    
    return '\n\n'.join(text_parts)


def extract_email_addresses(header_str):
    """Extract email addresses from header string."""
    import re
    # Match email addresses like "Name <email@domain.com>" or "email@domain.com"
    pattern = r'[\w\.-]+@[\w\.-]+\.\w+'
    return re.findall(pattern, header_str or '')


def connect_to_gmail(email_address, password):
    """Connect to Gmail via IMAP."""
    log(f"🔐 Connecting to Gmail: {email_address}")
    
    imap = imaplib.IMAP4_SSL('imap.gmail.com')
    imap.login(email_address, password)
    
    log(f"✅ Connected successfully")
    return imap


def fetch_emails(imap, folder='INBOX', since_days=30, limit=100):
    """Fetch emails from folder."""
    log(f"📧 Fetching emails from {folder} (last {since_days} days, limit {limit})")
    
    imap.select(folder)
    
    # Search criteria: emails since N days ago
    since_date = (datetime.now() - timedelta(days=since_days)).strftime("%d-%b-%Y")
    
    _, message_ids = imap.search(None, f'(SINCE {since_date})')
    
    if not message_ids[0]:
        log(f"   No emails found")
        return []
    
    ids = message_ids[0].split()
    
    # Limit number of emails
    if len(ids) > limit:
        log(f"   Found {len(ids)} emails, processing latest {limit}")
        ids = ids[-limit:]  # Get latest N emails
    else:
        log(f"   Found {len(ids)} emails")
    
    emails = []
    
    for i, email_id in enumerate(ids, 1):
        try:
            _, msg_data = imap.fetch(email_id, '(RFC822)')
            
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extract metadata
                    subject = decode_mime_header(msg['Subject'])
                    from_addr = decode_mime_header(msg['From'])
                    to_addr = decode_mime_header(msg['To'])
                    date = decode_mime_header(msg['Date'])
                    
                    # Extract body text
                    body = extract_email_text(msg)
                    
                    # Skip if body too short (likely notification)
                    if len(body) < 100:
                        continue
                    
                    # Extract email addresses
                    from_emails = extract_email_addresses(from_addr)
                    to_emails = extract_email_addresses(to_addr)
                    
                    emails.append({
                        'id': email_id.decode(),
                        'subject': subject,
                        'from': from_addr,
                        'from_emails': from_emails,
                        'to': to_addr,
                        'to_emails': to_emails,
                        'date': date,
                        'body': body[:5000]  # Limit body length for LLM
                    })
                    
                    if i % 10 == 0:
                        log(f"   Processed {i}/{len(ids)} emails...")
        
        except Exception as e:
            log(f"   Error processing email {email_id}: {e}")
    
    log(f"✅ Fetched {len(emails)} valid emails")
    return emails


def process_emails_with_groq(emails, ie_pipeline, db):
    """Process emails through Groq IE pipeline."""
    log(f"\n🤖 Processing emails with Groq...")
    
    total_entities = 0
    total_relations = 0
    
    for i, email_data in enumerate(emails, 1):
        try:
            # Prepare context for LLM
            context = f"""
Email Subject: {email_data['subject']}
From: {email_data['from']}
To: {email_data['to']}
Date: {email_data['date']}

Email Body:
{email_data['body']}
"""
            
            source_url = f"email:{email_data['id']}"
            
            log(f"\n   [{i}/{len(emails)}] Processing: {email_data['subject'][:60]}...")
            
            # Extract with Groq
            result = ie_pipeline.extract(
                text=context,
                source_url=source_url,
                source_type='email'
            )
            
            if not result:
                log(f"      ⚠️  No extraction result")
                continue
            
            # Entity Resolution
            resolved = resolve_entities(result['entities'])
            
            # Store in graph
            db.store_extraction(
                source_url=source_url,
                entities=resolved,
                relations=result['relations']
            )
            
            total_entities += len(resolved)
            total_relations += len(result['relations'])
            
            log(f"      ✅ {len(resolved)} entities, {len(result['relations'])} relations")
            
            # Rate limiting for free tier
            time.sleep(2)
        
        except Exception as e:
            log(f"      ❌ Error: {e}")
    
    log(f"\n✅ Processed {len(emails)} emails")
    log(f"   Total entities: {total_entities}")
    log(f"   Total relations: {total_relations}")


def main():
    """Main email pipeline."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process Gmail emails')
    parser.add_argument('--email', required=True, help='Gmail address')
    parser.add_argument('--password', help='Gmail app password (or use GMAIL_PASSWORD env var)')
    parser.add_argument('--folder', default='INBOX', help='IMAP folder (default: INBOX)')
    parser.add_argument('--since-days', type=int, default=30, help='Process emails from last N days')
    parser.add_argument('--limit', type=int, default=100, help='Max emails to process')
    
    args = parser.parse_args()
    
    # Get password
    password = args.password or os.environ.get('GMAIL_PASSWORD')
    
    if not password:
        print("❌ Error: Gmail password not provided")
        print("   Use --password or set GMAIL_PASSWORD environment variable")
        print("\n   To generate App Password:")
        print("   1. Go to https://myaccount.google.com/apppasswords")
        print("   2. Create new app password for 'Mail'")
        print("   3. Use that 16-character password")
        return 1
    
    # Groq API key
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if not groq_api_key:
        print("❌ Error: GROQ_API_KEY not set")
        return 1
    
    log("=" * 60)
    log("EMAIL PIPELINE")
    log("=" * 60)
    
    # Connect to Gmail
    try:
        imap = connect_to_gmail(args.email, password)
    except Exception as e:
        log(f"❌ Failed to connect to Gmail: {e}")
        return 1
    
    # Fetch emails
    try:
        emails = fetch_emails(
            imap, 
            folder=args.folder,
            since_days=args.since_days,
            limit=args.limit
        )
    except Exception as e:
        log(f"❌ Failed to fetch emails: {e}")
        return 1
    finally:
        imap.logout()
    
    if not emails:
        log("⚠️  No emails to process")
        return 0
    
    # Initialize IE pipeline
    ie_pipeline = IEPipeline(api_key=groq_api_key)
    
    # Initialize graph DB
    db = GraphDB()
    
    # Process emails
    process_emails_with_groq(emails, ie_pipeline, db)
    
    # Show final stats
    log("\n" + "=" * 60)
    log("FINAL STATS")
    log("=" * 60)
    
    stats = db.get_stats()
    for key, val in stats.items():
        log(f"   {key}: {val}")
    
    db.close()
    
    log("\n✅ Email pipeline completed")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

