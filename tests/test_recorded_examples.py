"""Recorded review must preserve evidence and require no inference or DB import."""

import json
import unittest

from zubumafu.recorded_examples import EXAMPLES, ROOT, as_markdown, load_example


class RecordedExampleTests(unittest.TestCase):
    def test_selected_dialogues_are_exact_subsets_of_accepted_evidence(self):
        self.assertTrue(3 <= len(EXAMPLES) <= 5)
        for example in EXAMPLES:
            with self.subTest(example=example.key):
                original = (ROOT / example.evidence_file).read_bytes()
                report = json.loads(original)
                recording = load_example(example.key)
                self.assertTrue(report['passed'])
                self.assertEqual(recording['turns'], report['turns'][:example.turn_count])
                exported = as_markdown(recording)
                for turn in recording['turns']:
                    self.assertIn(turn['question'], exported)
                    self.assertIn(turn['answer'], exported)
                self.assertEqual((ROOT / example.evidence_file).read_bytes(), original)

    def test_order_record_preserves_redaction_and_excludes_independent_denials(self):
        recording = load_example('orders')
        self.assertEqual(len(recording['turns']), 3)
        self.assertEqual(recording['turns'][-1]['question'], '[REDACTED_EMAIL]')
        self.assertFalse(any(turn['scenario'] in ('wrong_email', 'nonexistent_order')
                             for turn in recording['turns']))
        self.assertNotRegex(as_markdown(recording), r'[\w.+-]+@[\w.-]+\.[a-zA-Z]{2,}')
        self.assertIn('R$ 359,00', recording['turns'][-1]['answer'])

    def test_catalog_excludes_independent_quality_checks_and_marks_controller_lookup(self):
        recording = load_example('catalog')
        self.assertEqual([turn['scenario'] for turn in recording['turns']],
                         ['catalog', 'steel_followup'])
        self.assertEqual(recording['turns'][1]['model_requests'], [])
        self.assertIn('without a model call', as_markdown(recording))


if __name__ == '__main__':
    unittest.main()
