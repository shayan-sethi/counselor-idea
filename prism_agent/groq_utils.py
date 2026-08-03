import os
import time
import requests

GROQ_ENDPOINT = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "llama-3.3-70b-versatile"


def get_groq_api_keys():
    """
    Retrieves configured Groq API keys in priority order:
    1. GROQ_API_KEY / GROQ_API_KEY_1
    2. GROQ_API_KEY_2
    3. GROQ_API_KEY_3
    4. GROQ_API_KEY_4 (and higher)
    5. GROQ_API_KEY_SECONDARY, GROQ_API_KEY_TERTIARY, GROQ_API_KEY_BACKUP
    6. Comma-separated keys in GROQ_API_KEYS
    """
    keys = []
    
    env_vars = [
        "GROQ_API_KEY",
        "GROQ_API_KEY_1",
        "GROQ_API_KEY_2",
        "GROQ_API_KEY_3",
        "GROQ_API_KEY_4",
        "GROQ_API_KEY_SECONDARY",
        "GROQ_API_KEY_TERTIARY",
        "GROQ_API_KEY_BACKUP"
    ]
    
    for var in env_vars:
        val = os.environ.get(var, "").strip().strip('"').strip("'")
        if val and val not in keys:
            keys.append(val)

    # Dynamic scan for any GROQ_API_KEY_<int>
    for var, val in sorted(os.environ.items()):
        if var.startswith("GROQ_API_KEY_") and var.split("GROQ_API_KEY_")[-1].isdigit():
            cleaned = val.strip().strip('"').strip("'")
            if cleaned and cleaned not in keys:
                keys.append(cleaned)

    # Also check GROQ_API_KEYS (comma separated)
    multi_keys = os.environ.get("GROQ_API_KEYS", "").strip()
    if multi_keys:
        for k in multi_keys.split(","):
            cleaned = k.strip().strip('"').strip("'")
            if cleaned and cleaned not in keys:
                keys.append(cleaned)
                
    return keys


def groq_post_with_retry(payload, label="Groq", max_wait=10, initial_key=None):
    """
    Multi-Key Groq API Execution Engine with Fallback:
    - Sequentially tries Key 1 -> Key 2 -> Key 3 -> Key 4 (and any additional configured keys).
    - If all Groq API keys rate-limit (HTTP 429/503) or fail, falls back seamlessly to the hardcoded/deterministic system.
    """
    available_keys = get_groq_api_keys()
    
    if initial_key and initial_key.strip():
        k_clean = initial_key.strip().strip('"').strip("'")
        if k_clean not in available_keys:
            available_keys.insert(0, k_clean)

    if not available_keys:
        print(f"[{label}] No Groq API keys configured. Dropping to deterministic/hardcoded system.")
        return None, "No Groq API keys available."

    delays = [2]
    last_err = "unknown"

    for tier_idx, current_key in enumerate(available_keys, start=1):
        masked_key = current_key[:8] + "..." if len(current_key) > 8 else "set"
        print(f"[{label}] Trying Key #{tier_idx} ({masked_key})...")
        
        deadline = time.time() + max_wait
        for attempt, delay in enumerate(delays + [0], start=1):
            try:
                res = requests.post(
                    GROQ_ENDPOINT,
                    headers={"Authorization": f"Bearer {current_key}", "Content-Type": "application/json"},
                    json=payload,
                    timeout=30,
                )
                if res.status_code == 200:
                    if tier_idx > 1:
                        print(f"[{label}] Groq Key #{tier_idx} succeeded after Key #{tier_idx - 1} rate-limit!")
                    return res, None
                elif res.status_code in (429, 503):
                    last_err = f"HTTP {res.status_code} (rate-limit / overload) on Key #{tier_idx}"
                    print(f"[{label}] Key #{tier_idx} rate-limited (HTTP {res.status_code}).")
                else:
                    last_err = f"HTTP {res.status_code}: {res.text[:200]}"
                    print(f"[{label}] Key #{tier_idx} returned HTTP {res.status_code}.")
                    return None, last_err
            except Exception as exc:
                last_err = str(exc)
                print(f"[{label}] Key #{tier_idx} request exception: {exc}")

            if time.time() + delay > deadline or delay == 0:
                break
            time.sleep(delay)

        if tier_idx < len(available_keys):
            print(f"[{label}] Rate limit hit on Key #{tier_idx}. Falling back to Key #{tier_idx + 1}...")

    print(f"[{label}] All {len(available_keys)} Groq API keys rate-limited or failed. Falling back to hardcoded system.")
    return None, f"All {len(available_keys)} Groq keys rate-limited/failed. Last error: {last_err}"
