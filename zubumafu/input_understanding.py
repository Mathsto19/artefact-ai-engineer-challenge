"""Small spelling/abbreviation aliases for intent, never identity or prices."""

import re

from .catalog import _normalize


_INTENT_ALIASES = {
    'vc': 'voce', 'vcs': 'voces', 'qto': 'quanto', 'qnto': 'quanto',
    'td': 'tudo', 'bm': 'bem',
    'violau': 'violao', 'vlao': 'violao', 'violaoo': 'violao',
    'guitara': 'guitarra',
    'devouver': 'devolver', 'devolcao': 'devolucao', 'dvolucao': 'devolucao',
    'pixx': 'pix',
}


def normalize_intent(message: str) -> str:
    """Recognize common wording variants; do not rewrite the original message."""
    return re.sub(r'\b\w+\b', lambda match: _INTENT_ALIASES.get(match[0], match[0]), _normalize(message))


def is_greeting(message: str) -> bool:
    normalized = normalize_intent(message)
    # Punctuation is ignored only for a whole-message greeting. A price, order
    # or policy question appended to it cannot enter this fast path.
    normalized = ' '.join(re.sub(r'[^\w\s]', '', normalized).split())
    return bool(re.fullmatch(
        r'(oi+|ui|oy|oie+|ola+|bom dia|boa tarde|boa noite|e ai)( zubumafu)?( tudo (bem|bom))?', normalized))
