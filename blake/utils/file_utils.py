
import re
from typing import Optional

def sanitize_filename(text: str, max_length: int = 50) -> str:
    """
    Sanitize text for use in filenames.
    
    Args:
        text: Text to sanitize (usually work title)
        max_length: Maximum length of the sanitized string
        
    Returns:
        Sanitized string suitable for filenames
    """
    if not text:
        return "untitled"
        
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces and special chars with underscore
    text = re.sub(r'[^\w\d-]', '_', text)
    
    # Replace multiple underscores with single one
    text = re.sub(r'_+', '_', text)
    
    # Remove leading/trailing underscores
    text = text.strip('_')
    
    # Truncate
    if len(text) > max_length:
        text = text[:max_length].rstrip('_')
        
    return text
