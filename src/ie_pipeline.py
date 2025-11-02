"""IE Pipeline using Groq API (Llama 3.1 70B)."""

import json
import os
import time
from typing import Dict, Any, Optional
from groq import Groq
from prompts import build_prompt


class IEPipeline:
    """Information Extraction Pipeline."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize Groq client."""
        api_key = api_key or os.environ.get("GROQ_API_KEY")
        if not api_key:
            raise ValueError("GROQ_API_KEY not found in environment")
        self.client = Groq(api_key=api_key)
        # Updated model: llama-3.3-70b-versatile (новая версия)
        self.model = "llama-3.3-70b-versatile"  
        self.max_retries = int(os.getenv("MAX_RETRIES", "3"))
    
    def extract(self, text: str, source_type: str = "media", source_url: str = "") -> Dict[str, Any]:
        """
        Extract entities and relations from text.
        
        Args:
            text: Document text
            source_type: Type of source ("linkedin", "media", "website_bio", "interview")
            source_url: Source URL for logging
            
        Returns:
            Dict with "entities" and "relations"
        """
        prompt = build_prompt(text, source_type)
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.1,  # Low temp для консистентности
                    max_tokens=4000,
                    response_format={"type": "json_object"}  # Force JSON output
                )
                
                content = response.choices[0].message.content
                result = json.loads(content)
                
                # Validate structure
                if "entities" not in result or "relations" not in result:
                    raise ValueError(f"Invalid response structure: {result.keys()}")
                
                # Add source metadata
                result["source_url"] = source_url
                result["source_type"] = source_type
                result["model"] = self.model
                
                return result
                
            except json.JSONDecodeError as e:
                print(f"⚠️  JSON decode error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    return {"entities": [], "relations": [], "error": str(e)}
                time.sleep(2 ** attempt)  # Exponential backoff
                
            except Exception as e:
                print(f"⚠️  API error (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(2 ** attempt)
        
        return {"entities": [], "relations": [], "error": "Max retries exceeded"}
    
    def detect_source_type(self, url: str) -> str:
        """Detect source type from URL."""
        url_lower = url.lower()
        
        if "linkedin.com" in url_lower:
            return "linkedin"
        elif any(word in url_lower for word in ["interview", "интервью", "беседа"]):
            return "interview"
        elif any(word in url_lower for word in ["about", "bio", "profile", "о-нас", "обо-мне"]):
            return "website_bio"
        else:
            return "media"

