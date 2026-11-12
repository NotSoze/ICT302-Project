"""Regression cases for Word RSID data and missing metadata.

No confidential document samples or network access are needed.
"""
import base64
import tempfile
import unittest
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path

from core.xml_parser import XMLParser, usable_rsid
from core.metrics_calculator import MetricsCalculator
from core.document_reader import analyze_buffers, read_docx
from core.analysis_store import AnalysisStore

W = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'


def xml_doc(content):
    return ET.fromstring(f'<w:document xmlns:w="{W}"><w:body>{content}</w:body></w:document>')


def xml_settings(root='11111111', values=''):
    return ET.fromstring(f'<w:settings xmlns:w="{W}"><w:rsids><w:rsidRoot w:val="{root}"/>{values}</w:rsids></w:settings>')


class ForensicParserTests(unittest.TestCase):
    def test_run_inherits_default_not_paragraph_addition_rsid(self):
        doc = xml_doc('<w:p w:rsidR="11111111" w:rsidRDefault="22222222"><w:r><w:t>Hello world</w:t></w:r></w:p>')
        para = XMLParser({'document_xml': doc, 'settings_xml': xml_settings()}).parse_document_structure()[0]
        self.assertEqual(para['runs'][0]['rsidR'], '22222222')
        self.assertEqual(para['runs'][0]['session_type'], 'Other')
        self.assertEqual(para['session_type'], 'Root')

    def test_split_word_counted_once_and_attributed_once(self):
        doc = xml_doc('<w:p w:rsidRDefault="22222222"><w:r w:rsidR="33333333"><w:t>Hel</w:t></w:r><w:r><w:t>lo world</w:t></w:r></w:p>')
        parser = XMLParser({'document_xml': doc, 'settings_xml': xml_settings()})
        para = parser.parse_document_structure()[0]
        self.assertEqual(para['word_count'], 2)
        self.assertEqual([r['word_count'] for r in para['runs']], [1, 1])
        m = MetricsCalculator([para], {}).compute_macro_metrics()
        self.assertEqual(sum(m['session_word_aggregates'].values()), 2)
        self.assertEqual(m['total_word_count'], 2)

    def test_all_zero_rsid_no_valid_sessions_and_no_fake_revision(self):
        doc = xml_doc('<w:p w:rsidR="00000000" w:rsidRDefault="00000000"><w:r w:rsidR="00000000"><w:t>Hello there</w:t></w:r></w:p>')
        parser = XMLParser({'document_xml': doc, 'settings_xml': xml_settings(root='00000000')})
        para = parser.parse_document_structure()[0]
        self.assertEqual(para['session_type'], 'Unavailable')
        self.assertIsNone(para['runs'][0]['rsidR'])
        self.assertEqual(parser.generate_timeline_player_sequence([para]), [])
        metrics = MetricsCalculator([para], {'revision_count': None}).compute_macro_metrics()
        self.assertEqual(metrics['unique_rsid_count'], 0)
        self.assertEqual(metrics['session_word_aggregates'], {})
        self.assertIsNone(metrics['revision_count'])
        self.assertIsNone(metrics['word_to_revision_ratio'])
        self.assertIsNone(metrics['unique_rsid_to_revision_ratio'])

    def test_unusable_rsid_values(self):
        for invalid in (None, '', '0', '00000000', '0000abcdx', 'wat'):
            self.assertIsNone(usable_rsid(invalid))
        self.assertEqual(usable_rsid('00Ab01cD'), '00AB01CD')

    def test_multiple_text_nodes_and_tabs_are_included(self):
        doc = xml_doc('<w:p w:rsidRDefault="22222222"><w:r><w:t>First</w:t><w:tab/><w:t>second</w:t></w:r></w:p>')
        para = XMLParser({'document_xml': doc}).parse_document_structure()[0]
        self.assertEqual(para['text'], 'First\tsecond')
        self.assertEqual(para['word_count'], 2)

    def test_document_order_not_settings_order(self):
        doc = xml_doc('<w:p w:rsidRDefault="AAAA0001"><w:r><w:t>A</w:t></w:r></w:p>'
                      '<w:p w:rsidRDefault="BBBB0002"><w:r><w:t>B</w:t></w:r></w:p>')
        settings = xml_settings(values='<w:rsid w:val="BBBB0002"/><w:rsid w:val="AAAA0001"/>')
        parser = XMLParser({'document_xml': doc, 'settings_xml': settings})
        self.assertEqual([x['rsid'] for x in parser.generate_timeline_player_sequence(parser.parse_document_structure())],
                         ['AAAA0001', 'BBBB0002'])

    def test_extended_metadata_and_absence_are_distinct(self):
        parser = XMLParser({})
        self.assertIsNone(parser.extract_core_metadata()['revision_count'])
        app = ET.fromstring('<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
                                  '<Application>Microsoft Word</Application><TotalTime>0</TotalTime>'
                                  '<Pages>4</Pages><SharedDoc>false</SharedDoc></Properties>')
        meta = XMLParser({'app_xml': app}).extract_core_metadata()
        self.assertEqual(meta['editing_time_minutes'], 0)
        self.assertEqual(meta['page_count'], 4)
        self.assertFalse(meta['shared_document'])

    def test_transparent_large_group_review_indicator(self):
        doc = xml_doc('<w:p w:rsidRDefault="11111111"><w:r><w:t>' + ' '.join(['word'] * 120) + '</w:t></w:r></w:p>')
        parser = XMLParser({'document_xml': doc, 'settings_xml': xml_settings()})
        metrics = MetricsCalculator(parser.parse_document_structure(), {}).compute_macro_metrics()
        self.assertEqual(metrics['largest_rsid_share_percent'], 100.0)
        self.assertEqual(metrics['descriptive_indicators'][0]['code'], 'large_rsid_group')
        self.assertIn('does not prove', metrics['descriptive_indicators'][0]['description'])

    def test_analyze_buffers_has_data_availability_notices(self):
        doc = xml_doc('<w:p w:rsidR="00000000"><w:r><w:t>Test</w:t></w:r></w:p>')
        result = analyze_buffers({'document_xml': doc})
        self.assertTrue(result['success'])
        self.assertEqual(result['session_sequence'], [])
        self.assertTrue(any('unavailable' in note.lower() for note in result['analysis_notices']))


class IntegrationTests(unittest.TestCase):
    def test_valid_docx_runs_and_report_is_real_pdf(self):
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            docx = folder / 'sample.docx'
            parts = {
                '[Content_Types].xml': ('<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                    '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/></Types>'),
                '_rels/.rels': '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>',
                'word/document.xml': ET.tostring(xml_doc('<w:p w:rsidR="11111111" w:rsidRDefault="22222222">'
                         '<w:r><w:t>This is a test.</w:t></w:r></w:p>')),
                'word/settings.xml': ET.tostring(xml_settings()),
            }
            with zipfile.ZipFile(docx, 'w') as z:
                for name, data in parts.items():
                    z.writestr(name, data)
            result = read_docx(docx.name, base64.b64encode(docx.read_bytes()).decode('ascii'))
            self.assertTrue(result.get('success'), result)
            self.assertTrue(result.get('integrity_verified'))
            self.assertEqual(result['metrics']['total_word_count'], 4)
            store = AnalysisStore(folder / 'sessions')
            sid = store.save(docx.name, result)
            self.assertEqual(store.open(sid)[1]['sha256'], result['sha256'])
            report = store.export(sid, folder / 'forensic-report.pdf')
            self.assertTrue(report.read_bytes().startswith(b'%PDF-'))
            self.assertGreater(report.stat().st_size, 1000)

    def test_docx_only_gate_rejects_legacy_extension(self):
        from core.doc_handler import handle_upload
        with tempfile.TemporaryDirectory() as folder:
            folder = Path(folder)
            source = folder / 'legacy.doc'
            source.write_bytes(b'\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1' + b'\x00' * 80)
            ok, msg, _ = handle_upload(source, folder / 'copy')
            self.assertFalse(ok)
            self.assertIn('.doc', msg)


if __name__ == '__main__':
    unittest.main()
