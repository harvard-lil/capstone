# monkeypatch reporters-db with some variations specific to our OCR

from reporters_db import REPORTERS

EXTRA_VARIATIONS = {
    'Iowa Reports': {'Iowa': ['la.']},
    'Vermont Reports': {'Vt.': ['Yt.']},
    'Pacific Reporter': {
        'P.': ['Pae.', 'R'],
        'P.2d': ['R2d'],
        'P.3d': ['R3d'],
    },
    "West's Supreme Court Reporter": {'S. Ct.': ['5.Ct.']},
}

for reporter_key, reporter_cluster in REPORTERS.items():
    for cluster_index, reporter in enumerate(reporter_cluster):
        variations = reporter["variations"]

        # apply manual variations
        if reporter['name'] in EXTRA_VARIATIONS:
            for edition_key, extra_variations in EXTRA_VARIATIONS[reporter['name']].items():
                for variation in extra_variations:
                    variations[variation] = edition_key

        # Add "F. (2d)" as variation for "F. 2d"
        candidates = [(k, k) for k in reporter['editions']] + [(k, v) for k, v in variations.items()]
        for k, v in candidates:
            for t in ['2d', '3d']:
                if k.endswith(t):
                    variations[k.replace(t, f'({t})')] = v


# temporarily patch eyecite with simpler page number regex
import eyecite.utils
eyecite.utils.PAGE_NUMBER_REGEX = r"(?:%s)" % "|".join(
    [
        r"\d+",  # simple digit
        eyecite.utils.ROMAN_NUMERAL_REGEX,
        eyecite.utils.ROMAN_NUMERAL_REGEX.lower(),
        r"[*¶]*[\d:\-]+",  # ¶, star, colon
    ]
)
