"""Persistence, chat isolation and source-of-evidence tests (no Streamlit needed)."""

import tempfile
import json
import subprocess
import sys
import unittest
from pathlib import Path

from zubumafu.conversations import ConversationStore, DEFAULT_DB
from zubumafu.demo_scenarios import SCENARIOS, SCENARIO_BY_KEY


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / "private_history.sqlite3"
        self.store = ConversationStore(self.path)

    def tearDown(self):
        self.folder.cleanup()

    def test_history_survives_new_store_instance(self):
        first = self.store.create()
        self.store.add_exchange(first, "Quero um violão", "Encontrei opções.", [{"tool": "search_products", "status": "ok"}])
        reopened = ConversationStore(self.path)
        self.assertEqual(len(reopened.messages(first)), 2)
        self.assertEqual(reopened.messages(first)[0]["content"], "Quero um violão")
        self.assertEqual(reopened.list_all()[0]["title"], "Quero um violão")

    def test_history_survives_a_separate_python_process(self):
        chat = self.store.create()
        self.store.add_exchange(chat, 'Persistence check', 'Stored answer')
        result = subprocess.run([sys.executable, '-c',
            'import json,sys; from pathlib import Path; from zubumafu.conversations import ConversationStore; print(json.dumps(ConversationStore(Path(sys.argv[1])).messages(sys.argv[2])))',
            str(self.path), chat], capture_output=True, text=True, check=True, timeout=10)
        self.assertEqual(json.loads(result.stdout)[-1]['content'], 'Stored answer')

    def test_source_provenance_survives_storage_without_raw_payloads(self):
        chat = self.store.create()
        details = {'tool': 'search_store_policies', 'status': 'ok',
                   'references': [{'chapter': 4, 'pages': [4]}],
                   'ambiguities': [{'issue': 'contact_conflict', 'note': 'Confirm the conflicting numbers.'}],
                   'filters': {'query': 'private@example.org', 'email': 'private@example.org'},
                   'reply_origin': 'source_verified_clarification_template',
                   'raw_tool_result': {'text': 'private reasoning'}}
        self.store.add_exchange(chat, 'Question', 'Answer', [details])
        saved = self.store.messages(chat)[1]['trace'][0]
        self.assertEqual(saved['references'], details['references'])
        self.assertEqual(saved['ambiguities'], details['ambiguities'])
        self.assertEqual(saved['reply_origin'], details['reply_origin'])
        self.assertNotIn('email', saved['filters'])
        self.assertNotIn('private@example.org', str(saved))
        self.assertNotIn('raw_tool_result', saved)

    def test_separate_chats_do_not_mix_history(self):
        one = self.store.create()
        two = self.store.create()
        self.store.add_exchange(one, "Pergunta um", "Resposta um")
        self.store.add_exchange(two, "Pergunta dois", "Resposta dois")
        self.assertEqual([msg["content"] for msg in self.store.messages(one)], ["Pergunta um", "Resposta um"])
        self.assertEqual([msg["content"] for msg in self.store.messages(two)], ["Pergunta dois", "Resposta dois"])

    def test_email_is_redacted_from_sidebar_title(self):
        chat = self.store.create()
        self.store.add_exchange(chat, "Meu e-mail é teste@example.org, consulte o pedido", "Qual é o número?")
        self.assertNotIn("teste@example.org", self.store.get(chat)["title"])
        # Stored messages are a local history, not anonymized evidence.
        self.assertIn("teste@example.org", self.store.messages(chat)[0]["content"])

    def test_trace_does_not_persist_customer_identifiers_or_email(self):
        chat = self.store.create()
        self.store.add_exchange(chat, "123", "Consulta", [{
            "tool": "get_order_status", "status": "verified", "email": "private@example.org",
            "customer_id": 7, "raw_tool_result": {"address": "sensitive"},
        }])
        trace = self.store.messages(chat)[1]["trace"]
        self.assertEqual(trace, [{"tool": "get_order_status", "status": "verified"}])

    def test_test_scenario_is_labeled_but_no_fake_messages_are_seeded(self):
        key = SCENARIOS[0].key
        chat = self.store.create(kind="test", scenario_id=key, title=SCENARIOS[0].title)
        record = self.store.get(chat)
        self.assertEqual(record["kind"], "test")
        self.assertIn(record["scenario_id"], SCENARIO_BY_KEY)
        self.assertEqual(self.store.messages(chat), [])

    def test_delete_removes_only_one_conversation_and_messages(self):
        first = self.store.create()
        second = self.store.create()
        self.store.add_exchange(first, "Olá", "Oi")
        self.store.add_exchange(second, "Teste", "Ok")
        self.assertTrue(self.store.delete(first))
        self.assertIsNone(self.store.get(first))
        self.assertEqual(len(self.store.messages(second)), 2)

    def test_invalid_conversation_type_and_missing_id_are_rejected(self):
        with self.assertRaises(ValueError):
            self.store.create(kind="private")
        with self.assertRaises(ValueError):
            self.store.create(kind="personal", scenario_id="catalog")
        with self.assertRaises(KeyError):
            self.store.add_exchange("unknown", "a", "b")

    def test_default_history_path_is_ignored_by_git(self):
        root = Path(__file__).resolve().parents[1]
        self.assertEqual(DEFAULT_DB.parent.name, ".local")
        self.assertIn(".local/", (root / ".gitignore").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
