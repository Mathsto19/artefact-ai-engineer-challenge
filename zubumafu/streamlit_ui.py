"""Messenger-style Streamlit demo with separate persisted chat histories.

This is NOT a WhatsApp integration: it is a single-user local prototype.
"""

from __future__ import annotations

import streamlit as st
import logging
import os
import sqlite3
import time
from pathlib import Path

from .agent import respond
from .ui_theme import THEMES, theme_css
from .conversations import ConversationStore, DEFAULT_DB
from .demo_scenarios import SCENARIOS, SCENARIO_BY_KEY
from .response_quality import clean_display_text, clean_display_value, split_answer_sources, chat_markdown
from .recorded_examples import EXAMPLES, EXAMPLE_BY_KEY, load_example, recorded_date, as_markdown

logger = logging.getLogger(__name__)


def show_trace(trace, answer="", elapsed_seconds=None):
    _, sources = split_answer_sources(answer)
    if not trace and not sources and elapsed_seconds is None:
        return
    with st.expander("Fontes e ferramentas consultadas"):
        if elapsed_seconds is not None:
            st.caption(f"Tempo registrado: {elapsed_seconds:.2f} s")
        for source in sources:
            st.caption(source)
        for item in trace or []:
            pages = f" · páginas {item['pages']}" if item.get("pages") else ""
            st.caption(clean_display_text(f"{item['tool']} · {item['status']}{pages}"))
            details = {key: item[key] for key in ('source', 'sources', 'filters', 'references',
                       'ambiguities', 'pricing', 'order_id', 'reply_origin', 'invoked_by',
                       'argument_overrides') if item.get(key) is not None}
            if details:
                st.json(clean_display_value(details))


def show_recorded_example(key: str) -> None:
    try:
        recording = load_example(key)
    except (OSError, ValueError, KeyError):
        st.error("Não consegui abrir o registro desta conversa. Confira os arquivos do projeto.")
        return
    example = recording["example"]
    st.subheader(example.title)
    st.caption(f"Conversa registrada · {recorded_date(recording)} · {recording['model']}")
    st.write("Exemplo para leitura. As mensagens abaixo já foram registradas; abrir esta conversa não executa o modelo.")
    with st.expander("Sobre esta conversa"):
        st.write(example.note)
        st.caption(f"Registro original: {example.evidence_file}")
        st.caption("As respostas usam os arquivos demonstrativos. Não representam estoque ou rastreamento ao vivo.")
    st.download_button("Baixar conversa (.md)", data=as_markdown(recording),
                       file_name=f"zubumafu-{key}.md", mime="text/markdown",
                       key=f"download_recorded_{key}")
    for turn in recording["turns"]:
        with st.chat_message("Cliente", avatar=":material/person:"):
            st.markdown(chat_markdown(turn["question"]))
        with st.chat_message("Zubumafu", avatar=":material/graphic_eq:"):
            st.markdown(chat_markdown(split_answer_sources(turn["answer"])[0]))
            show_trace(turn.get("trace"), turn["answer"], turn['elapsed_seconds'])


def main() -> None:
    st.set_page_config(page_title="Zubumafu | Empório da Música", page_icon=":material/graphic_eq:",
                       layout="wide", initial_sidebar_state="collapsed")

    st.session_state.setdefault("navigation_open", True)
    if "ui_theme" not in st.session_state:
        requested_theme = st.query_params.get("theme", "system")
        st.session_state.ui_theme = next((name for name, value in THEMES.items()
                                         if value == requested_theme), "Sistema")

    def save_theme() -> None:
        st.query_params["theme"] = THEMES[st.session_state.ui_theme]

    with st.container(key="app_controls", horizontal=True, vertical_alignment="center"):
        if st.button("Ocultar conversas" if st.session_state.navigation_open else "Abrir conversas",
                     key="toggle_navigation", icon=":material/menu:"):
            st.session_state.navigation_open = not st.session_state.navigation_open
            st.rerun()
        with st.popover("Aparência", icon=":material/contrast:"):
            st.selectbox("Tema", list(THEMES), key="ui_theme", on_change=save_theme)
    st.markdown(theme_css(st.session_state.ui_theme), unsafe_allow_html=True)

    @st.cache_resource
    def get_store(path: str) -> ConversationStore:
        return ConversationStore(Path(path))


    try:
        store = get_store(os.environ.get("ZUBUMAFU_HISTORY_PATH", str(DEFAULT_DB)))
        all_chats = store.list_all()
    except (sqlite3.Error, OSError):
        st.error("Não consegui abrir o histórico local. Confira o arquivo e as permissões antes de tentar novamente.")
        st.stop()
    if "chat_id" not in st.session_state or store.get(st.session_state.chat_id) is None:
        st.session_state.chat_id = all_chats[0]["id"] if all_chats else store.create()


    def switch_chat(chat_id: str) -> None:
        st.session_state.chat_id = chat_id
        st.session_state.pop("recorded_example", None)
        st.session_state.confirm_delete = False
        st.session_state.pop("queued_question", None)


    if st.session_state.navigation_open:
        navigation, content = st.columns([1, 3], gap="medium")
        with navigation:
            with st.container(key="conversation_navigation"):
                render_navigation(store, switch_chat)
    else:
        content = st.container()
    # At the main root Streamlit anchors the composer to the viewport bottom.
    # Inside the conversation column it becomes inline and precedes new replies.
    question = None
    if st.session_state.get("recorded_example") not in EXAMPLE_BY_KEY:
        question = st.chat_input("Escreva sua mensagem para o Zubumafu...", key="message_input")
    with content:
        with st.container(key="conversation_content"):
            render_conversation(store, switch_chat, question)


def render_navigation(store, switch_chat) -> None:
    st.markdown('''<div class="zubu-brand"><span class="zubu-sidebar-title">Zubumafu</span>
                <span class="zubu-brand-subtitle">Empório da Música</span></div>''', unsafe_allow_html=True)
    if st.button("Nova conversa", key="new_chat", type="primary", icon=":material/add:", use_container_width=True):
        switch_chat(store.create())
        st.rerun()

    st.markdown('<p class="zubu-nav-heading">Minhas conversas</p>', unsafe_allow_html=True)
    st.markdown('<p class="zubu-nav-label">Exemplos para avaliação</p>', unsafe_allow_html=True)
    for example in EXAMPLES:
        if st.button(example.title, key=f"recorded_{example.key}", use_container_width=True,
                     type="primary" if st.session_state.get("recorded_example") == example.key else "secondary",
                     help="Abrir conversa registrada, sem executar o modelo"):
            st.session_state.recorded_example = example.key
            st.session_state.confirm_delete = False
            st.session_state.pop("queued_question", None)
            st.rerun()

    chats = store.list_all()
    personal_chats = [item for item in chats if item["kind"] == "personal"]
    st.markdown('<p class="zubu-nav-label">Suas conversas</p>', unsafe_allow_html=True)
    if not personal_chats:
        st.caption("Comece uma conversa para vê-la aqui.")
    for item in personal_chats:
        if st.button(clean_display_text(item['title']), key=f"chat_{item['id']}",
                     use_container_width=True,
                     type="primary" if item["id"] == st.session_state.chat_id and not st.session_state.get("recorded_example") else "secondary"):
            switch_chat(item["id"])
            st.rerun()

    st.markdown('<p class="zubu-nav-heading">Conversas de teste</p>', unsafe_allow_html=True)
    for item in (entry for entry in chats if entry["kind"] == "test"):
        if st.button(clean_display_text(item['title']), key=f"test_chat_{item['id']}", use_container_width=True,
                     type="primary" if item["id"] == st.session_state.chat_id and not st.session_state.get("recorded_example") else "secondary"):
            switch_chat(item["id"])
            st.rerun()
    with st.expander("Iniciar um teste"):
        st.caption("Perguntas sugeridas; as respostas são geradas ao executar.")
        for scenario in SCENARIOS:
            if st.button(scenario.title, key=f"new_scenario_{scenario.key}", use_container_width=True):
                switch_chat(store.create(kind="test", scenario_id=scenario.key,
                                         title=scenario.title))
                st.rerun()

    st.divider()
    st.caption("Histórico salvo neste computador.")
    with st.expander("Sobre este protótipo"):
        st.caption("Dados demonstrativos. Sem conexão com WhatsApp ou autenticação de produção.")
        st.caption("As mensagens, inclusive e-mails digitados, são salvas localmente sem criptografia. Exclua conversas sensíveis quando terminar.")


def render_conversation(store, switch_chat, question=None) -> None:
    conversation = store.get(st.session_state.chat_id)
    scenario = SCENARIO_BY_KEY.get(conversation["scenario_id"]) if conversation["kind"] == "test" else None
    st.markdown("""
    <div class="zubu-banner">
      <h2>Assistente do Empório da Música</h2>
      <p>Consulte instrumentos, preços, políticas e pedidos.</p>
    </div>
    """, unsafe_allow_html=True)
    recorded_key = st.session_state.get("recorded_example")
    if recorded_key in EXAMPLE_BY_KEY:
        show_recorded_example(recorded_key)
        return
    header, remove_column = st.columns([5, 1], vertical_alignment="center")
    with header:
        st.subheader(("Teste · " if scenario else "") + clean_display_text(conversation["title"]))
        if scenario:
            st.caption("Cenário de validação: respostas reais só aparecem após executar a pergunta.")
    with remove_column:
        if st.button("Excluir", key="delete_chat", use_container_width=True):
            st.session_state.confirm_delete = True

    if st.session_state.get("confirm_delete"):
        st.warning("Excluir esta conversa e todas as mensagens salvas nela?")
        yes, no = st.columns(2)
        if yes.button("Sim, excluir", use_container_width=True):
            store.delete(st.session_state.chat_id)
            remaining = store.list_all()
            switch_chat(remaining[0]["id"] if remaining else store.create())
            st.rerun()
        if no.button("Manter conversa", use_container_width=True):
            st.session_state.confirm_delete = False
            st.rerun()

    if scenario:
        with st.expander("Perguntas e critérios deste teste", expanded=True):
            st.write(scenario.description)
            st.markdown("**Passos sugeridos**")
            for i, prompt in enumerate(scenario.prompts, start=1):
                if st.button(f"Enviar pergunta {i}: {prompt}", key=f"step_{conversation['id']}_{i}"):
                    st.session_state.queued_question = prompt
            st.markdown("**O que conferir na resposta**")
            for expected in scenario.expected:
                st.markdown(f"- {expected}")
            st.caption("Estes são critérios, não resultados já aprovados. Confira o rastreamento da ferramenta e registre a validação real.")


    messages = store.messages(st.session_state.chat_id)
    if not messages:
        with st.container(border=True):
            st.markdown("### Como posso ajudar?")
            st.write("Conte o que você procura ou tire uma dúvida sobre a loja.")
            st.caption('Por exemplo: "Quais violões disponíveis custam até R$ 1.000?"')
    for message in messages:
        with st.chat_message("Zubumafu" if message["role"] == "assistant" else "Você",
                             avatar=":material/graphic_eq:" if message["role"] == "assistant" else ":material/person:"):
            if message["role"] == "assistant":
                st.markdown(chat_markdown(split_answer_sources(message["content"])[0]))
                show_trace(message.get("trace"), message["content"])
            else:
                st.markdown(chat_markdown(message["content"]))

    queued = st.session_state.pop("queued_question", None)
    question = question or queued
    if question:
        prior = [{"role": item["role"], "content": item["content"]} for item in messages]
        with st.chat_message("Você", avatar=":material/person:"):
            st.markdown(chat_markdown(question))
        with st.chat_message("Zubumafu", avatar=":material/graphic_eq:"):
            status = st.status("Lendo sua mensagem", expanded=False)
            output = st.empty()
            started = time.perf_counter()
            current_stage = "Lendo sua mensagem"
            last_update = 0.0

            def show_event(event: dict) -> None:
                nonlocal current_stage, last_update
                elapsed = time.perf_counter() - started
                if event['type'] == 'stage':
                    current_stage = event['label']
                if event['type'] == 'answer':
                    output.markdown(chat_markdown(split_answer_sources(event['text'])[0]))
                if event['type'] != 'progress' or elapsed - last_update >= .25:
                    status.update(label=f"{current_stage} · {elapsed:.1f} s")
                    last_update = elapsed

            try:
                answer, trace = respond(question, history=prior, on_event=show_event)
                status.update(label=f"Resposta pronta · {time.perf_counter() - started:.1f} s",
                              state="complete", expanded=False)
            except Exception:
                logger.exception("Unable to complete the chat request")
                answer, trace = (
                    "Não consegui acessar o modelo local agora. Confira o Ollama e tente novamente.", []
                )
                status.update(label="Não consegui concluir a resposta", state="error", expanded=False)
            answer = clean_display_text(answer)
            output.markdown(chat_markdown(split_answer_sources(answer)[0]))
            show_trace(trace, answer)
        try:
            store.add_exchange(st.session_state.chat_id, question, answer, trace)
        except (sqlite3.Error, OSError):
            st.error("A resposta foi exibida, mas não consegui salvar esta conversa no histórico local.")
            st.stop()
        st.rerun()
