"""Exercise reruns, persisted threads, evidence and scoped deletion in Streamlit."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from zubumafu.conversations import ConversationStore


APP = str(Path(__file__).resolve().parents[1] / "app.py")


class StreamlitUITests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'history.sqlite3'
        self.environment = patch.dict(os.environ, {'ZUBUMAFU_HISTORY_PATH': str(self.path)})
        self.environment.start()
        self.store = ConversationStore(self.path)

    def tearDown(self):
        self.environment.stop()
        self.folder.cleanup()

    def test_reruns_switch_restart_and_delete_preserve_thread_isolation(self):
        trace = [{'tool': 'search_store_policies', 'status': 'ok', 'pages': [4],
                  'references': [{'chapter': 4, 'pages': [4]}], 'source': 'data/manual.pdf',
                  'reply_origin': 'source_verified_clarification_template'}]
        with patch('zubumafu.streamlit_ui.respond', return_value=('A compra foi online?', trace)) as backend:
            app = AppTest.from_file(APP).run(timeout=15)
            self.assertFalse(app.exception)
            first = app.session_state['chat_id']
            app.chat_input[0].set_value('Quero devolver meu instrumento').run(timeout=15)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.chat_message), 2)
            self.assertEqual(json.loads(app.json[0].value)['references'], trace[0]['references'])
            app.button(key='new_chat').click().run(timeout=15)
            second = app.session_state['chat_id']
            self.assertNotEqual(first, second)
            self.assertEqual(len(app.chat_message), 0)
            app.chat_input[0].set_value('Outra conversa').run(timeout=15)
            self.assertEqual(backend.call_args.kwargs['history'], [])
            app.button(key=f'chat_{first}').click().run(timeout=15)
            self.assertEqual(len(app.chat_message), 2)
            self.assertEqual(app.session_state['chat_id'], first)
            restarted = AppTest.from_file(APP).run(timeout=15)
            self.assertFalse(restarted.exception)
            restarted.button(key=f'chat_{first}').click().run(timeout=15)
            self.assertEqual(len(restarted.chat_message), 2)
            restarted.button(key='delete_chat').click().run(timeout=15)
            next(b for b in restarted.button if b.label == 'Manter conversa').click().run(timeout=15)
            self.assertIsNotNone(self.store.get(first))
            restarted.button(key='delete_chat').click().run(timeout=15)
            next(b for b in restarted.button if b.label == 'Sim, excluir').click().run(timeout=15)
            self.assertFalse(restarted.exception)
            self.assertIsNone(self.store.get(first))
            self.assertEqual(len(self.store.messages(second)), 2)

    def test_scenarios_start_empty_and_only_execute_on_request(self):
        trace = [{'tool': 'search_products', 'status': 'ok',
                  'invoked_by': 'application_reference_lookup',
                  'reply_origin': 'python_catalog_result_template'}]
        with patch('zubumafu.streamlit_ui.respond', return_value=('Resposta executada', trace)) as backend:
            app = AppTest.from_file(APP).run(timeout=15)
            app.button(key='new_scenario_catalog').click().run(timeout=15)
            test_id = app.session_state['chat_id']
            self.assertEqual(self.store.get(test_id)['kind'], 'test')
            self.assertFalse(backend.called)
            self.assertEqual(self.store.messages(test_id), [])
            app.button(key=f'step_{test_id}_1').click().run(timeout=15)
            self.assertFalse(app.exception)
            self.assertEqual(backend.call_count, 1)
            self.assertEqual(len(app.chat_message), 2)
            self.assertEqual(len(self.store.messages(test_id)), 2)
            self.assertEqual(json.loads(app.json[0].value)['invoked_by'], 'application_reference_lookup')

    def test_backend_error_is_saved_without_traceback_or_machine_details(self):
        with patch('zubumafu.streamlit_ui.respond', side_effect=ConnectionError('private machine address')), patch('zubumafu.streamlit_ui.logger.exception'):
            app = AppTest.from_file(APP).run(timeout=15)
            app.chat_input[0].set_value('Quero uma guitarra').run(timeout=15)
            self.assertFalse(app.exception)
            answer = self.store.messages(app.session_state['chat_id'])[-1]['content']
            self.assertIn('Ollama', answer)
            self.assertNotIn('private machine address', answer)


if __name__ == '__main__':
    unittest.main()
