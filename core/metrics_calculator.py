class MetricsCalculator:
    """
    Computes macro-level ratios and structural session volume rankings.
    """
    def __init__(self, parsed_paragraphs: list[dict], metadata: dict):
        self.paragraphs = parsed_paragraphs
        self.metadata = metadata

    def compute_macro_metrics(self) -> dict:
        """
        Calculates global document-level metrics:
        - Total Word Count (W)
        - Total Revision Count (R)
        - Unique RSIDs (U)
        - Word-to-Revision Ratio (W/R)
        - Unique RSID-to-Revision Ratio (U/R)
        - Session word aggregates and their corresponding session types
        """
        total_words = sum(p['word_count'] for p in self.paragraphs)
        revision_count = self.metadata.get('revision_count', 1)
        if revision_count < 1:
            revision_count = 1  # Prevent division by zero

        unique_rsids = set()
        session_word_aggregates = {}
        session_types = {}

        for p in self.paragraphs:
            rsid = p['paragraph_rsidR'] or p['paragraph_rsidDefault']
            if rsid:
                unique_rsids.add(rsid)
                session_word_aggregates[rsid] = session_word_aggregates.get(rsid, 0) + p['word_count']
                
                # Map the RSID to its classified session type (Primary vs Secondary/Other)
                if rsid not in session_types:
                    session_types[rsid] = p['session_type']

        u_count = len(unique_rsids)

        # Macro-level mathematical ratio calculations (Descriptive Indicators)
        w_r_ratio = total_words / revision_count
        u_r_ratio = u_count / revision_count

        return {
            'total_word_count': total_words,
            'revision_count': revision_count,
            'unique_rsid_count': u_count,
            'word_to_revision_ratio': round(w_r_ratio, 2),
            'unique_rsid_to_revision_ratio': round(u_r_ratio, 2),
            'session_word_aggregates': session_word_aggregates,
            'session_types': session_types
        }

    def generate_top_n_rankings(self, n: int = 5) -> list[dict]:
        """
        Generates a descriptive Top-N volume ranking of sessions by word count,
        returning structured dictionaries containing the RSID hex, word count, 
        and session type (Primary or Secondary/Other).
        """
        metrics = self.compute_macro_metrics()
        aggregates = metrics['session_word_aggregates']
        session_types = metrics.get('session_types', {})
        
        # Sort sessions descending by word count
        sorted_sessions = sorted(aggregates.items(), key=lambda item: item[1], reverse=True)
        
        top_n_list = []
        for rsid, word_count in sorted_sessions[:n]:
            top_n_list.append({
                'rsid': rsid,
                'word_count': word_count,
                'session_type': session_types.get(rsid, 'Secondary/Other')
            })
            
        return top_n_list