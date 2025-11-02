"""Utility functions."""

import requests
from bs4 import BeautifulSoup
from typing import Optional
import os


def fetch_url(url: str, timeout: int = None) -> Optional[str]:
    """
    Fetch content from URL (supports http/https and file://).
    
    Args:
        url: URL to fetch
        timeout: Request timeout in seconds
        
    Returns:
        Content or None if failed
    """
    timeout = timeout or int(os.getenv("REQUEST_TIMEOUT", "30"))
    
    try:
        # Handle file:// URLs
        if url.startswith("file://"):
            from pathlib import Path
            file_path = url.replace("file://", "")
            return Path(file_path).read_text(encoding='utf-8')
        
        # Handle HTTP/HTTPS
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.text
    except Exception as e:
        print(f"❌ Failed to fetch {url}: {e}")
        return None


def extract_text(html: str) -> str:
    """
    Extract clean text from HTML.
    
    Args:
        html: HTML content
        
    Returns:
        Cleaned text
    """
    soup = BeautifulSoup(html, "lxml")
    
    # Remove script and style elements
    for script in soup(["script", "style", "nav", "footer", "header"]):
        script.decompose()
    
    # Get text
    text = soup.get_text(separator="\n")
    
    # Clean up whitespace
    lines = (line.strip() for line in text.splitlines())
    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
    text = '\n'.join(chunk for chunk in chunks if chunk)
    
    return text


def generate_fact_id(relation: dict) -> str:
    """Generate unique fact ID from relation."""
    import hashlib
    
    # Create deterministic ID based on content
    content = f"{relation['subject']['name']}:{relation['relation']}:{relation['object']['name']}"
    return hashlib.md5(content.encode()).hexdigest()[:16]


def log(message: str, log_file: str = "logs/run.log"):
    """Write log message."""
    from datetime import datetime
    from pathlib import Path
    
    Path(log_file).parent.mkdir(exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    
    # Print to console
    print(log_line.rstrip())
    
    # Write to file
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(log_line)

