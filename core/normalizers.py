"""
Core text and phone normalization algorithms and string similarity metrics.
Zero external pip dependencies.
"""

import re

def normalize_phone(val):
    """Normalize phone numbers to uniform Egyptian 11-digit or digit strings."""
    if not val:
        return ""
    s = str(val).strip()
    if s.endswith('.0') and s[:-2].replace('-', '').replace('+', '').isdigit():
        s = s[:-2]
    digits = re.sub(r'\D', '', s)
    if digits.startswith('0020'):
        digits = digits[2:]  # leave leading '20'
    if digits.startswith('20') and len(digits) in (12, 13, 14):
        if len(digits) == 12:
            return '0' + digits[2:]
    if len(digits) == 10 and digits[0] == '1':
        return '0' + digits
    if len(digits) == 11 and digits.startswith('01'):
        return digits
    return digits

def normalize_arabic(text):
    """
    Standardize Arabic text:
    - Unify Hamzas (إ, أ, آ, ا -> ا)
    - Unify Teh Marbuta (ة -> ه)
    - Unify Alef Maksura (ى -> ي)
    - Strip Tashkeel diacritics
    - Normalize compound prefixes (عبد الرحمن -> عبدالرحمن, ابو الفتوح -> ابوالفتوح)
    """
    if not text:
        return ""
    text = str(text)
    # Strip Tashkeel
    text = re.sub(r'[\u064B-\u0652\u0640]', '', text)
    text = re.sub(r'[إأآا]', 'ا', text)
    text = re.sub(r'ة', 'ه', text)
    text = re.sub(r'ى', 'ي', text)
    text = re.sub(r'\bعبد\s+(\w+)', r'عبد\1', text)
    text = re.sub(r'\bابو\s+(\w+)', r'ابو\1', text)
    return text.strip()

def levenshtein_dist(s1, s2):
    """Fast, pure standard-library Levenshtein distance for fuzzy typo matching."""
    if s1 == s2:
        return 0
    if len(s1) == 0:
        return len(s2)
    if len(s2) == 0:
        return len(s1)
    # Optimization: limit to 40 chars max for speed
    s1, s2 = s1[:40], s2[:40]
    v0 = list(range(len(s2) + 1))
    v1 = [0] * (len(s2) + 1)
    for i in range(len(s1)):
        v1[0] = i + 1
        for j in range(len(s2)):
            cost = 0 if s1[i] == s2[j] else 1
            v1[j + 1] = min(v1[j] + 1, v0[j + 1] + 1, v0[j] + cost)
        v0 = v1[:]
    return v0[len(s2)]
