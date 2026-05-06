# AI Attribute Generation Fixes - Summary

## Overview
This document summarizes the fixes and improvements made to the AI attribute generation system in the NBA 2K26 Generator.

## Files Modified

### 1. `nba2k26_generator/ollama_attributes.py`

#### Changes Made:

**Configuration Improvements:**
- Added environment variable support for all configuration options:
  - `OLLAMA_URL` - API endpoint
  - `OLLAMA_TAGS_URL` - Tags endpoint
  - `OLLAMA_MODEL` - Model name (default: gemma2:9b)
  - `OLLAMA_TIMEOUT` - Request timeout
  - `OLLAMA_MAX_RETRIES` - Retry attempts
  - `OLLAMA_RETRY_DELAY` - Delay between retries
- Added in-memory caching (`_ai_cache`) to avoid redundant API calls

**Retry Logic:**
- Added `MAX_RETRIES` (default: 3) with exponential backoff
- Better error handling for different failure types:
  - Connection errors
  - Timeout errors
  - HTTP errors
  - General exceptions
- Each error type has appropriate retry strategy

**JSON Parsing Improvements:**
- Enhanced `extract_json_from_response()` with multiple fallback strategies:
  1. Markdown code blocks (```json ... ```)
  2. JSON between first { and last }
  3. Direct JSON parsing
  4. Regex extraction of key-value pairs
- Handles common JSON issues:
  - Trailing commas
  - Extra text before/after JSON
  - Malformed responses
- Better debug output when parsing fails

**New Functions:**
- `get_cache_key()` - Generates cache keys for player rows
- `check_ollama_available()` - Checks if Ollama is running and returns available models
- `clear_ai_cache()` - Clears the in-memory cache

**Prompt Improvements:**
- Added detailed rating scale guidance:
  - 25-35: G-League level
  - 40-50: End of bench
  - 55-65: Rotation player
  - 70-75: Starter quality
  - 80-85: Good starter
  - 88-92: All-Star level
  - 95-99: MVP level (rare)
- Added position-specific guidance for Guards, Wings, Bigs, and Stretch Bigs
- Better instructions for realistic ratings

**API Call Improvements:**
- Lower temperature (0.2 instead of 0.3) for more consistent results
- Added `top_p` and `top_k` parameters for better control
- Better verbose logging

---

### 2. `nba2k26_generator/ai_attribute_generator.py`

#### Changes Made:

**Import Fixes:**
- Added proper path handling for imports
- Graceful fallback between relative and absolute imports
- Better error messages when imports fail

**Enhanced `generate_attributes_hybrid()`:**
- Added `validate_ai_output` parameter (default: True)
- Added `max_ai_deviation` parameter (default: 15) for validation
- Added `skip_if_unavailable` parameter
- Better tracking of AI generation status:
  - `ai_failed_reason` - Why AI failed if it did
  - `blend_mode` - How final attributes were computed
  - `ai_attributes_converted` - AI attributes in generator format
- Early Ollama availability check to avoid unnecessary attempts
- Better exception handling with stack traces in verbose mode

**New Validation Function:**
- `validate_ai_against_heuristic()` - Compares AI output to heuristic:
  - Checks for missing attributes
  - Flags large deviations (>15 points)
  - Warns about unrealistic values (95+)
  - Returns list of validation issues

**Improved Blending Logic:**
- `blend_attributes()` now uses smart weighting:
  - Physical attributes (Speed, Agility, etc.): Reduced AI weight (×0.7)
    - AI often over/under-estimates physicals
  - Skill attributes (Shooting, Playmaking): Increased AI weight (×1.1)
    - AI is typically better at skill evaluation
- Better verbose output showing weight adjustments

**Enhanced Family Score Calculation:**
- `calculate_family_scores()` now handles both naming conventions:
  - Generator format: "Ball Handle"
  - Internal format: "ball_handle"
- Better attribute matching with normalized keys

**Better Overall Calculation:**
- Added clamping to ensure OVR stays in valid range (25-99)
- Maintains weighted formula favoring Shooting and Defense

**New Utility Functions:**
- `check_ai_status()` - Returns status of AI system
- `clear_ai_cache()` - Clears the AI cache
- `compare_ai_heuristic()` - Detailed comparison tool for debugging
  - Shows side-by-side AI vs heuristic values
  - Highlights large differences (≥10 points)
  - Useful for tuning and validation

**Improved Documentation:**
- Better docstrings with examples
- Clear parameter descriptions
- Usage examples in docstrings

---

## Benefits of These Changes

### 1. **Reliability**
- Retry logic ensures transient failures don't break generation
- Better error handling prevents crashes
- Fallback to heuristics is seamless

### 2. **Consistency**
- Lower temperature (0.2) produces more consistent AI results
- Caching prevents redundant API calls
- Validation catches unrealistic AI outputs

### 3. **Debugging**
- Verbose mode shows detailed information
- Validation reports highlight issues
- Comparison tool helps tune AI vs heuristic balance

### 4. **Flexibility**
- Environment variables allow easy configuration
- Multiple blend modes (AI-only, heuristic-only, blended)
- Adjustable validation thresholds

### 5. **Performance**
- In-memory caching speeds up repeated requests
- Early availability check avoids unnecessary API calls
- Efficient attribute matching

---

## Usage Examples

### Basic Usage (Full AI)
```python
from nba2k26_generator.ai_attribute_generator import generate_attributes_hybrid

result = generate_attributes_hybrid(player_row, verbose=True)
print(f"AI Generated: {result['ai_generated']}")
print(f"Overall: {result['overall']}")
```

### 50/50 Blend
```python
result = generate_attributes_hybrid(
    player_row,
    ai_weight=0.5,  # 50% AI, 50% heuristic
    verbose=True
)
```

### Force Heuristic Only
```python
result = generate_attributes_hybrid(
    player_row,
    use_ai=False
)
```

### Check AI Status
```python
from nba2k26_generator.ai_attribute_generator import check_ai_status

status = check_ai_status()
print(f"AI Available: {status['available']}")
print(f"Models: {status['models_available']}")
```

### Compare AI vs Heuristic
```python
from nba2k26_generator.ai_attribute_generator import compare_ai_heuristic

comparison = compare_ai_heuristic(player_row, verbose=True)
```

---

## Environment Variables

Set these in your environment or `.env` file:

```bash
# Ollama Configuration
OLLAMA_URL=http://localhost:11434/api/generate
OLLAMA_TAGS_URL=http://localhost:11434/api/tags
OLLAMA_MODEL=gemma2:9b
OLLAMA_TIMEOUT=300
OLLAMA_MAX_RETRIES=3
OLLAMA_RETRY_DELAY=1.0
```

---

## Testing

Run the module directly to test:

```bash
python -m nba2k26_generator.ai_attribute_generator
```

Or test Ollama integration:

```bash
python -m nba2k26_generator.ollama_attributes
```

---

## Future Improvements

Potential future enhancements:

1. **Persistent Caching**: Save AI results to disk for reuse across sessions
2. **Batch Processing**: Generate multiple players in one API call
3. **Model Selection**: Auto-select best available model
4. **A/B Testing**: Compare different models systematically
5. **Fine-tuning**: Train custom model on historical 2K ratings
6. **Confidence Scores**: Have AI output confidence for each attribute

---

## Troubleshooting

### Ollama Not Available
- Ensure Ollama is running: `ollama serve`
- Check model is pulled: `ollama pull gemma2:9b`
- Verify URL is correct in environment variables

### AI Generation Fails
- Check verbose output for specific error
- Verify JSON parsing with debug mode
- Try increasing retry count

### Unrealistic Attributes
- Enable validation: `validate_ai_output=True`
- Reduce `max_ai_deviation` threshold
- Adjust blend weight toward heuristics

### Slow Performance
- Enable caching (on by default)
- Check network latency to Ollama
- Consider local Ollama instance
