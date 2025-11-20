"""
Robust JSON extraction utilities for LLM responses.
Handles various formats and edge cases in AI-generated JSON.
"""
import json
import re
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


def extract_json_from_llm_response(
    response: str,
    fallback: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Extract JSON from LLM response with multiple fallback strategies.
    
    Tries:
    1. Standard { } extraction
    2. Markdown code blocks (```json)
    3. Multiple JSON objects (takes first)
    4. Line-by-line parsing
    5. Returns fallback if all fail
    
    Args:
        response: Raw LLM response string
        fallback: Default value if extraction fails
        
    Returns:
        Parsed JSON dictionary or fallback
        
    Raises:
        ValueError: If extraction fails and no fallback provided
    """
    if not response or not isinstance(response, str):
        if fallback is not None:
            return fallback
        raise ValueError("Empty or invalid response")
    
    # Strategy 1: Standard JSON extraction
    try:
        result = _extract_standard_json(response)
        if result:
            return result
    except Exception as e:
        logger.debug(f"Standard JSON extraction failed: {e}")
    
    # Strategy 2: Markdown code block extraction
    try:
        result = _extract_markdown_json(response)
        if result:
            return result
    except Exception as e:
        logger.debug(f"Markdown JSON extraction failed: {e}")
    
    # Strategy 3: Find first complete JSON object
    try:
        result = _extract_first_json_object(response)
        if result:
            return result
    except Exception as e:
        logger.debug(f"First JSON object extraction failed: {e}")
    
    # Strategy 4: Clean and retry
    try:
        result = _extract_cleaned_json(response)
        if result:
            return result
    except Exception as e:
        logger.debug(f"Cleaned JSON extraction failed: {e}")
    
    # All strategies failed
    if fallback is not None:
        logger.warning(f"All JSON extraction strategies failed, using fallback")
        return fallback
    
    raise ValueError(f"Could not extract JSON from response: {response[:200]}...")


def _extract_standard_json(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON using standard { } markers."""
    json_start = response.find('{')
    json_end = response.rfind('}') + 1
    
    if json_start >= 0 and json_end > json_start:
        json_str = response[json_start:json_end]
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            # Try fixing common errors before giving up
            logger.debug(f"Initial JSON parse failed: {e}, attempting fix...")
            try:
                fixed_json = _fix_common_json_errors(json_str)
                return json.loads(fixed_json)
            except Exception as fix_error:
                logger.debug(f"Fix attempt also failed: {fix_error}")
                raise e  # Re-raise original error
    
    return None


def _extract_markdown_json(response: str) -> Optional[Dict[str, Any]]:
    """Extract JSON from markdown code blocks."""
    # Try ```json format with optional newline
    pattern = r'```json\s*(.*?)```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        content = match.group(1).strip()
        print(f"[JSON Parser] Extracted from ```json block, length: {len(content)}")
        print(f"[JSON Parser] First 200 chars: {content[:200]}")
        try:
            result = json.loads(content)
            print(f"[JSON Parser] Successfully parsed JSON from ```json block")
            return result
        except json.JSONDecodeError as e:
            print(f"[JSON Parser] JSON parse failed: {e}, trying fix...")
            print(f"[JSON Parser] Error context: {content[max(0, e.pos-50):min(len(content), e.pos+50)]}")
            # Try fixing common errors
            try:
                fixed = _fix_common_json_errors(content)
                result = json.loads(fixed)
                print(f"[JSON Parser] Successfully parsed after fix")
                return result
            except json.JSONDecodeError as fix_e:
                print(f"[JSON Parser] Fix also failed: {fix_e}")
                print(f"[JSON Parser] Error context after fix: {fixed[max(0, fix_e.pos-50):min(len(fixed), fix_e.pos+50)]}")
    else:
        print(f"[JSON Parser] No match for ```json pattern in response (length: {len(response)})")
    
    # Try generic ``` format with optional newline
    pattern = r'```\s*(.*?)```'
    match = re.search(pattern, response, re.DOTALL)
    if match:
        content = match.group(1).strip()
        print(f"[JSON Parser] Extracted from ``` block, length: {len(content)}")
        # Check if it's JSON
        if content.startswith('{'):
            print(f"[JSON Parser] Content starts with '{{', attempting parse...")
            try:
                result = json.loads(content)
                print(f"[JSON Parser] Successfully parsed JSON from ``` block")
                return result
            except json.JSONDecodeError as e:
                print(f"[JSON Parser] JSON parse failed: {e}, trying fix...")
                print(f"[JSON Parser] Error context: {content[max(0, e.pos-50):min(len(content), e.pos+50)]}")
                # Try fixing common errors
                try:
                    fixed = _fix_common_json_errors(content)
                    result = json.loads(fixed)
                    print(f"[JSON Parser] Successfully parsed after fix")
                    return result
                except json.JSONDecodeError as fix_e:
                    print(f"[JSON Parser] Fix also failed: {fix_e}")
                    print(f"[JSON Parser] Error context after fix: {fixed[max(0, fix_e.pos-50):min(len(fixed), fix_e.pos+50)]}")
        else:
            print(f"[JSON Parser] Content doesn't start with {{ (starts with: {content[:50]})")
    else:
        print(f"[JSON Parser] No match for ``` pattern")
    
    return None


def _extract_first_json_object(response: str) -> Optional[Dict[str, Any]]:
    """Find and extract the first complete JSON object."""
    stack = []
    start_idx = None
    
    for i, char in enumerate(response):
        if char == '{':
            if not stack:
                start_idx = i
            stack.append(char)
        elif char == '}':
            if stack:
                stack.pop()
                if not stack and start_idx is not None:
                    # Found complete JSON object
                    json_str = response[start_idx:i+1]
                    try:
                        return json.loads(json_str)
                    except json.JSONDecodeError:
                        # Continue searching
                        start_idx = None
    
    return None


def _extract_cleaned_json(response: str) -> Optional[Dict[str, Any]]:
    """Clean response and try parsing again."""
    # Remove common LLM prefixes
    prefixes = [
        "Here's the JSON:",
        "Here is the JSON:",
        "The result is:",
        "Result:",
        "Output:",
        "Response:",
    ]
    
    cleaned = response
    for prefix in prefixes:
        if prefix in cleaned:
            cleaned = cleaned.split(prefix, 1)[1]
    
    # Remove leading/trailing whitespace
    cleaned = cleaned.strip()
    
    # Try standard extraction on cleaned version
    result = _extract_standard_json(cleaned)
    
    # If still failing, try fixing common JSON errors
    if result is None:
        try:
            json_start = cleaned.find('{')
            json_end = cleaned.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = cleaned[json_start:json_end]
                fixed_json = _fix_common_json_errors(json_str)
                return json.loads(fixed_json)
        except:
            pass
    
    return result


def _fix_common_json_errors(json_str: str) -> str:
    """
    Fix common JSON errors that LLMs make.
    
    Common issues:
    - Range values like "2-3" instead of numbers
    - Trailing commas
    - Unquoted keys
    """
    original_len = len(json_str)
    
    # Fix range values like "2-3" -> "2" (take first number)
    # This handles cases like "quantity": 2-3
    json_str = re.sub(r':\s*(\d+)-\d+\s*,', r': \1,', json_str)
    json_str = re.sub(r':\s*(\d+)-\d+\s*}', r': \1}', json_str)
    
    # Fix fractions like "1/2" -> "0.5" (before comma or closing brace)
    def convert_fraction(match):
        numerator = float(match.group(1))
        denominator = float(match.group(2))
        return f': {numerator/denominator}{match.group(3)}'
    
    json_str = re.sub(r':\s*(\d+)/(\d+)(\s*[,}])', convert_fraction, json_str)
    
    # Fix fractional ranges like "1/2-1" -> "0.5"
    json_str = re.sub(r':\s*(\d+)/(\d+)-[\d/]+\s*,', lambda m: f': {float(m.group(1))/float(m.group(2))},', json_str)
    
    # Remove trailing commas before } or ]
    json_str = re.sub(r',(\s*[}\]])', r'\1', json_str)
    
    if len(json_str) != original_len:
        print(f"🔧 Fixed JSON errors: {original_len} -> {len(json_str)} chars")
    
    return json_str


def extract_json_array(response: str) -> Optional[list]:
    """
    Extract JSON array from LLM response.
    
    Args:
        response: Raw LLM response string
        
    Returns:
        Parsed JSON array or None
    """
    # Try to find array markers
    array_start = response.find('[')
    array_end = response.rfind(']') + 1
    
    if array_start >= 0 and array_end > array_start:
        try:
            json_str = response[array_start:array_end]
            return json.loads(json_str)
        except json.JSONDecodeError:
            pass
    
    return None


def safe_json_parse(json_str: str, fallback: Any = None) -> Any:
    """
    Safely parse JSON string with fallback.
    
    Args:
        json_str: JSON string to parse
        fallback: Value to return if parsing fails
        
    Returns:
        Parsed JSON or fallback value
    """
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, TypeError, ValueError) as e:
        logger.warning(f"JSON parse failed: {e}")
        return fallback


def validate_json_schema(
    data: Dict[str, Any],
    required_fields: list,
    raise_on_missing: bool = False
) -> bool:
    """
    Validate that JSON has required fields.
    
    Args:
        data: Dictionary to validate
        required_fields: List of required field names
        raise_on_missing: Whether to raise ValueError on missing fields
        
    Returns:
        True if all fields present, False otherwise
        
    Raises:
        ValueError: If raise_on_missing=True and fields are missing
    """
    missing = [field for field in required_fields if field not in data]
    
    if missing:
        if raise_on_missing:
            raise ValueError(f"Missing required fields: {missing}")
        return False
    
    return True


# Convenience function for common use case
def parse_llm_json(
    response: str,
    required_fields: Optional[list] = None,
    fallback: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Parse LLM JSON response and optionally validate schema.
    
    Args:
        response: Raw LLM response
        required_fields: Optional list of required fields
        fallback: Fallback value if parsing fails
        
    Returns:
        Parsed and validated JSON dictionary
    """
    result = extract_json_from_llm_response(response, fallback=fallback)
    
    if required_fields:
        validate_json_schema(result, required_fields, raise_on_missing=False)
    
    return result
