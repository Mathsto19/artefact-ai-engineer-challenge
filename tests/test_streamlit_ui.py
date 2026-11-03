"""Exercise reruns, persisted threads, evidence and scoped deletion in Streamlit."""

import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

from zubumafu.conversations import ConversationStore
from zubumafu.recorded_examples import EXAMPLES, load_example
from zubumafu.response_quality import clean_display_text, split_answer_sources, chat_markdown


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
        citation = 'Fonte consultada: Manual de políticas v2.1, seção(ões) 4, página(s) 4.'
        original_answer = f'A compra foi online?\n\n*{citation}*'
        with patch('zubumafu.streamlit_ui.respond', return_value=(original_answer, trace)) as backend:
            app = AppTest.from_file(APP).run(timeout=15)
            self.assertFalse(app.exception)
            first = app.session_state['chat_id']
            app.chat_input[0].set_value('Quero devolver meu instrumento').run(timeout=15)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.chat_message), 2)
            self.assertEqual(json.loads(app.json[0].value)['references'], trace[0]['references'])
            self.assertEqual([item.value for item in app.chat_message[1].markdown], ['A compra foi online?'])
            sources = next(item for item in app.expander if item.label == 'Fontes e ferramentas consultadas')
            self.assertIn(citation, [item.value for item in sources.caption])
            self.assertEqual(self.store.messages(first)[-1]['content'], original_answer)
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
        with patch('zubumafu.streamlit_ui.respond', return_value=('Resposta executada 🎸', trace)) as backend:
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
            self.assertEqual(self.store.messages(test_id)[-1]['content'], 'Resposta executada')
            self.assertTrue(all('🎸' not in item.value for item in app.markdown))

    def test_backend_error_is_saved_without_traceback_or_machine_details(self):
        with patch('zubumafu.streamlit_ui.respond', side_effect=ConnectionError('private machine address')), patch('zubumafu.streamlit_ui.logger.exception'):
            app = AppTest.from_file(APP).run(timeout=15)
            app.chat_input[0].set_value('Quero uma guitarra').run(timeout=15)
            self.assertFalse(app.exception)
            answer = self.store.messages(app.session_state['chat_id'])[-1]['content']
            self.assertIn('Ollama', answer)
            self.assertNotIn('private machine address', answer)

    def test_brl_quotes_render_as_text_in_both_themes_without_changing_history(self):
        answer = ('**Kalani KAL-700T Tenor Natural**\n'
                  'Preço de tabela: **R$ 359,00**.\n'
                  'Promoção ativa: **10% de desconto**. Preço final: **R$ 323,10**.')
        question = 'Cabe em R$ 340? E em R$ 300?'
        with patch('zubumafu.streamlit_ui.respond', return_value=(answer, [])):
            app = AppTest.from_file(APP).run(timeout=15)
            app.chat_input[0].set_value(question).run(timeout=15)
            for theme in ('Escuro', 'Claro'):
                app.selectbox(key='ui_theme').set_value(theme).run(timeout=15)
                self.assertFalse(app.exception)
                body = app.chat_message[1].markdown[0].value
                self.assertIn('**R\\$ 359,00**.', body)
                self.assertIn('**R\\$ 323,10**.', body)
                self.assertIn('Natural**  \nPreço', body)
                self.assertIn('**10% de desconto**', body)
                self.assertEqual(app.chat_message[0].markdown[0].value,
                                 'Cabe em R\\$ 340? E em R\\$ 300?')
            messages = self.store.messages(app.session_state['chat_id'])
            self.assertEqual(messages[-1]['content'], answer)
            self.assertEqual(messages[-2]['content'], question)

    def test_recorded_conversations_open_without_inference_or_private_history_changes(self):
        with patch('zubumafu.streamlit_ui.respond') as backend:
            app = AppTest.from_file(APP).run(timeout=15)
            personal_id = app.session_state['chat_id']
            before = self.store.list_all()
            for example in EXAMPLES:
                app.button(key=f'recorded_{example.key}').click().run(timeout=15)
                self.assertFalse(app.exception)
                self.assertEqual(len(app.chat_message), example.turn_count * 2)
                self.assertEqual(len(app.chat_input), 0)
                self.assertFalse(any(button.key == 'delete_chat' for button in app.button))
                rendered = '\n'.join(item.value for item in app.markdown)
                for turn in load_example(example.key)['turns']:
                    self.assertIn(chat_markdown(turn['question']), rendered)
                    self.assertIn(chat_markdown(split_answer_sources(turn['answer'])[0]), rendered)
                self.assertNotIn('Fonte consultada:', rendered)
                self.assertNotIn('resultado(s) do arquivo;', rendered)
                self.assertNotIn('Condição consultada nos arquivos fornecidos', rendered)
                for turn, message in zip(load_example(example.key)['turns'], list(app.chat_message)[1::2]):
                    details = next(item for item in message.expander if item.label == 'Fontes e ferramentas consultadas')
                    captions = [item.value for item in details.caption]
                    self.assertIn(f"Tempo registrado: {turn['elapsed_seconds']:.2f} s", captions)
                    for note in split_answer_sources(turn['answer'])[1]:
                        self.assertIn(note, captions)
                self.assertEqual(self.store.list_all(), before)
                self.assertEqual(self.store.messages(personal_id), [])
            backend.assert_not_called()
            app.button(key=f'chat_{personal_id}').click().run(timeout=15)
            self.assertEqual(len(app.chat_input), 1)
            self.assertEqual(len(app.chat_message), 0)
            app.button(key='recorded_catalog').click().run(timeout=15)
            app.button(key='new_chat').click().run(timeout=15)
            self.assertEqual(len(app.chat_input), 1)
            self.assertNotEqual(app.session_state['chat_id'], personal_id)
            self.assertEqual(len(app.chat_message), 0)
            self.assertNotIn('recorded_example', app.session_state)

    def test_missing_record_shows_error_without_generating_a_replacement(self):
        with patch('zubumafu.streamlit_ui.respond') as backend:
            app = AppTest.from_file(APP).run(timeout=15)
            with patch('zubumafu.streamlit_ui.load_example', side_effect=FileNotFoundError):
                app.button(key='recorded_catalog').click().run(timeout=15)
            self.assertFalse(app.exception)
            self.assertEqual(len(app.error), 1)
            self.assertEqual(len(app.chat_message), 0)
            self.assertEqual(len(app.chat_input), 0)
            backend.assert_not_called()

    def test_progress_and_partial_output_save_only_the_completed_exchange(self):
        def backend(question, history, on_event):
            self.assertEqual(history, [])
            on_event({'type': 'stage', 'label': 'Preparando a resposta'})
            on_event({'type': 'progress'})
            on_event({'type': 'answer', 'text': 'Texto parcial', 'complete': False})
            on_event({'type': 'answer', 'text': 'Resposta concluída', 'complete': True})
            return 'Resposta concluída', []
        with patch('zubumafu.streamlit_ui.respond', side_effect=backend):
            app = AppTest.from_file(APP).run(timeout=15)
            app.chat_input[0].set_value('Pode me ajudar?').run(timeout=15)
            self.assertFalse(app.exception)
            messages = self.store.messages(app.session_state['chat_id'])
            self.assertEqual([item['content'] for item in messages],
                             ['Pode me ajudar?', 'Resposta concluída'])
            self.assertEqual(len(app.chat_message), 2)

    def test_navigation_can_always_reopen_in_both_themes_without_losing_selection(self):
        with patch('zubumafu.streamlit_ui.respond') as backend:
            app = AppTest.from_file(APP).run(timeout=15)
            personal_id = app.session_state['chat_id']
            self.store.add_exchange(personal_id, 'Minha pergunta', 'Minha resposta')
            app.button(key=f'chat_{personal_id}').click().run(timeout=15)
            for theme in ('Escuro', 'Claro'):
                app.selectbox(key='ui_theme').set_value(theme).run(timeout=15)
                self.assertFalse(app.exception)
                self.assertEqual(len(app.chat_message), 2)
                app.button(key='toggle_navigation').click().run(timeout=15)
                self.assertEqual(app.button(key='toggle_navigation').label, 'Abrir conversas')
                self.assertFalse(app.session_state['navigation_open'])
                self.assertFalse(any(button.key == 'new_chat' for button in app.button))
                self.assertEqual(len(app.chat_message), 2)
                self.assertEqual(app.selectbox(key='ui_theme').value, theme)
                app.button(key='toggle_navigation').click().run(timeout=15)
                self.assertTrue(app.session_state['navigation_open'])
                self.assertEqual(app.button(key='toggle_navigation').label, 'Ocultar conversas')
                self.assertTrue(any(button.key == f'chat_{personal_id}' for button in app.button))
                self.assertEqual(app.session_state['chat_id'], personal_id)
                self.assertEqual(self.store.messages(personal_id)[-1]['content'], 'Minha resposta')
            backend.assert_not_called()

    def test_theme_survives_query_link_and_navigation_controls_exist_on_recordings(self):
        with patch('zubumafu.streamlit_ui.respond') as backend:
            app = AppTest.from_file(APP)
            app.query_params['theme'] = 'dark'
            app.run(timeout=15)
            self.assertEqual(app.selectbox(key='ui_theme').value, 'Escuro')
            app.button(key='recorded_orders').click().run(timeout=15)
            app.button(key='toggle_navigation').click().run(timeout=15)
            self.assertEqual(app.button(key='toggle_navigation').label, 'Abrir conversas')
            self.assertEqual(len(app.chat_message), 6)
            app.selectbox(key='ui_theme').set_value('Claro').run(timeout=15)
            self.assertEqual(app.query_params['theme'], 'light')
            self.assertEqual(len(app.chat_message), 6)
            self.assertEqual(len(app.chat_input), 0)
            backend.assert_not_called()


if __name__ == '__main__':
    unittest.main()
