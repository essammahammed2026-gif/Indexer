"""
Query parser supporting Google-style search operators:
- Exact phrases: "word1 word2"
- Exclude terms: -term
- OR / AND boolean logic
- File extension filter: filetype:pdf
"""

import re

def parse_google_query(raw_query):
    """
    Parses Google-style search operators:
    - Exact phrases: "word1 word2"
    - Exclude words: -term
    - OR logic: term1 OR term2
    - AND logic: term1 AND term2
    - File extension filter: filetype:pdf or filetype:xlsx
    Returns dict: fts_match, filetype, exact_phrases, clean_tokens.
    """
    clean = (raw_query or "").strip()
    if not clean:
        return {"fts_match": "", "filetype": None, "exact_phrases": [], "clean_tokens": []}

    # 1. filetype:ext
    filetype = None
    ft_m = re.search(r"\bfiletype:([a-zA-Z0-9]+)\b", clean, re.IGNORECASE)
    if ft_m:
        filetype = ft_m.group(1).lower().strip()
        clean = re.sub(r"\bfiletype:[a-zA-Z0-9]+\b", " ", clean, flags=re.IGNORECASE).strip()

    # 2. Extract exact phrases in quotes "..."
    exact_phrases = [p.strip() for p in re.findall(r"\"([^\"]+)\"", clean) if p.strip()]
    clean_no_quotes = re.sub(r"\"[^\"]*\"", " ", clean).strip()

    # 3. Parse negative terms (-term)
    tokens = clean_no_quotes.split()
    pos_tokens = []
    neg_tokens = []
    for t in tokens:
        if t.startswith("-") and len(t) > 1:
            term = t[1:].strip("(),:;\"'")
            if term:
                neg_tokens.append(term)
        else:
            pos_tokens.append(t)

    # 4. Handle OR / AND logic in remaining positive tokens
    pos_str = " ".join(pos_tokens)
    fts_parts = []

    # Add exact phrases
    for ph in exact_phrases:
        clean_ph = ph.replace('"', '')
        fts_parts.append(f'"{clean_ph}"')

    or_split = re.split(r"\s+OR\s+", pos_str, flags=re.IGNORECASE)
    if len(or_split) > 1:
        sub_fts = []
        for segment in or_split:
            words = [w.strip("(),:;\"'") for w in segment.split() if w.strip("(),:;\"'") and w.upper() != "AND"]
            if words:
                sub_fts.append(" AND ".join([f'""{w}""' for w in words]))
        if sub_fts:
            fts_parts.append("(" + " OR ".join(sub_fts) + ")")
    else:
        words = [w.strip("(),:;\"'") for w in pos_str.split() if w.strip("(),:;\"'") and w.upper() != "AND"]
        for w in words:
            fts_parts.append(f'""{w}""')

    fts_match = " AND ".join(fts_parts) if fts_parts else ""

    for nt in neg_tokens:
        clean_nt = nt.replace('"', '')
        if fts_match:
            fts_match += f' NOT ""{clean_nt}""'

    clean_tokens = [w for w in pos_str.split() if w.upper() not in ("OR", "AND")] + exact_phrases

    return {
        "fts_match": fts_match,
        "filetype": filetype,
        "exact_phrases": exact_phrases,
        "clean_tokens": [t.strip("(),:;\"'") for t in clean_tokens if t.strip("(),:;\"'")]
    }
