"""Document-level descriptive measurements; no misconduct or authorship verdicts."""
from core.xml_parser import usable_rsid


class MetricsCalculator:
    def __init__(self, parsed_paragraphs: list[dict], metadata: dict):
        self.paragraphs = parsed_paragraphs
        self.metadata = metadata

    def compute_macro_metrics(self) -> dict:
        total_words = sum(p['word_count'] for p in self.paragraphs)
        revision = self.metadata.get('revision_count')
        # Missing/zero is NOT equivalent to one revision.
        revision_count = revision if isinstance(revision, int) and not isinstance(revision, bool) and revision > 0 else None
        aggregates = {}
        types = {}
        chars = {}
        text_run_count = 0
        for p in self.paragraphs:
            for run in p.get('runs', []):
                if run.get('text'):
                    text_run_count += 1
                rsid = usable_rsid(run.get('rsidR'))
                if not rsid:
                    continue
                aggregates[rsid] = aggregates.get(rsid, 0) + run.get('word_count', 0)
                chars[rsid] = chars.get(rsid, 0) + run.get('character_count', len(run.get('text', '')))
                types.setdefault(rsid, run.get('session_type', 'Other'))
        unique = len(aggregates)
        attributed_words = sum(aggregates.values())
        largest_count = max(aggregates.values(), default=0)
        largest_share = round(largest_count / total_words * 100, 1) if total_words and unique else None
        # Transparent, non-validated review threshold; this is NOT a cheating
        # probability or evidence of pasting. Useful for FR-8 human review.
        indicators = []
        if total_words >= 100 and largest_share is not None and largest_share >= 60:
            indicators.append({
                'code': 'large_rsid_group',
                'description': f'One usable RSID group covers {largest_share}% of extracted words (review threshold: 60%, for documents with at least 100 words). This is a descriptive flag only; it does not prove a paste event or misconduct.',
            })
        return {
            'total_word_count': total_words,
            'revision_count': revision_count,
            'unique_rsid_count': unique,
            'word_to_revision_ratio': round(total_words / revision_count, 2) if revision_count else None,
            'unique_rsid_to_revision_ratio': round(unique / revision_count, 2) if revision_count else None,
            'session_word_aggregates': aggregates,
            'session_types': types,
            'text_run_count': text_run_count,
            'attributed_word_count': attributed_words,
            'largest_rsid_word_count': largest_count if unique else None,
            'largest_rsid_share_percent': largest_share,
            'descriptive_indicators': indicators,
            'average_characters_per_rsid': round(sum(chars.values()) / unique, 1) if unique else None,
            'average_characters_per_run': round(
                sum(r.get('character_count', len(r.get('text', ''))) for p in self.paragraphs for r in p.get('runs', [])) / text_run_count, 1
            ) if text_run_count else None,
        }

    def generate_top_n_rankings(self, n: int = 5) -> list[dict]:
        metrics = self.compute_macro_metrics()
        return [{
            'rsid': rsid,
            'word_count': words,
            'session_type': metrics['session_types'].get(rsid, 'Other'),
        } for rsid, words in sorted(metrics['session_word_aggregates'].items(),
                                   key=lambda entry: (-entry[1], entry[0]))[:n]]
