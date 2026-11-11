import re


_PREDICTABLE_PATTERN = re.compile(
    r"1234|2345|3456|4567|5678|6789|abcd|bcde|cdef|defg|efgh|fghi|ghij|hijk|ijkl|jklm|klmn|lmno|mnop|qwer|asdf|zxcv|password|admin|letmein|welcome",
    re.IGNORECASE | re.ASCII,
)


def password_strength_score(password: str) -> int:
    """Return the registration password score from 0 to 10."""
    if not password:
        return 0

    score = 0
    length = len(password)
    score += 2 if length >= 8 else 0
    score += 1 if length >= 12 else 0
    score += 1 if length >= 16 else 0

    score += int(bool(re.search(r"[a-z]", password)))
    score += int(bool(re.search(r"[A-Z]", password)))
    score += int(bool(re.search(r"[0-9]", password)))
    score += int(bool(re.search(r"[^a-zA-Z0-9]", password)))

    unique_ratio = len(set(password)) / length
    if unique_ratio >= 0.75:
        score += 1
    elif unique_ratio < 0.5:
        score -= 2
    if _PREDICTABLE_PATTERN.search(password):
        score -= 2

    return max(0, min(10, score))
