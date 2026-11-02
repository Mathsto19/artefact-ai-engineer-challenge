"""Messenger-style Streamlit demo with separate persisted chat histories.

This is NOT a WhatsApp integration: it is a single-user local prototype.
"""

from __future__ import annotations

import streamlit as st
import logging
import os
import sqlite3
from pathlib import Path

from .agent import respond
from .conversations import ConversationStore, DEFAULT_DB
from .demo_scenarios import SCENARIOS, SCENARIO_BY_KEY
from .response_quality import strip_emojis
from .recorded_examples import EXAMPLES, EXAMPLE_BY_KEY, load_example, recorded_date, as_markdown

logger = logging.getLogger(__name__)


def show_trace(trace):
    if not trace:
        return
    with st.expander("Fontes e ferramentas consultadas"):
        for item in trace:
            pages = f" · páginas {item['pages']}" if item.get("pages") else ""
            st.caption(f"{item['tool']} · {item['status']}{pages}")
            details = {key: item[key] for key in ('source', 'sources', 'filters', 'references',
                       'ambiguities', 'pricing', 'order_id', 'reply_origin', 'invoked_by',
                       'argument_overrides') if item.get(key) is not None}
            if details:
                st.json(details)


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
            st.markdown(strip_emojis(turn["question"]))
        with st.chat_message("Zubumafu", avatar=":material/graphic_eq:"):
            st.markdown(strip_emojis(turn["answer"]))
            st.caption(f"Tempo registrado: {turn['elapsed_seconds']:.2f} s")
            show_trace(turn.get("trace"))


def main() -> None:
    st.set_page_config(page_title="Zubumafu | Empório da Música", page_icon=":material/graphic_eq:",
                       layout="wide", initial_sidebar_state="expanded")

    st.markdown("""
    <style>
        :root { color-scheme: light; }
        .stApp { background: #f4f7f6; color: #18332f; }
        [data-testid="stHeader"] { background: #f4f7f6; }
        [data-testid="stToolbar"] { display: none; }
        [data-testid="stMainBlockContainer"] {
            max-width: 1120px; padding: 2rem 2.5rem 4rem;
        }
        [data-testid="stSidebar"] { background: #fff; border-right: 1px solid #dde6e2; }
        [data-testid="stSidebarUserContent"] { padding-top: 1.5rem; }
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 8px; justify-content: flex-start;
            text-align: left; min-height: 2.65rem;
        }
        .stButton > button { border-radius: 8px; }
        .stButton > button[kind="primary"] {
            background: #116b5b; border-color: #116b5b; color: #fff;
        }
        .stButton > button[kind="secondary"] {
            background: #fff; border-color: #d7e2dd; color: #18332f;
        }
        .stButton > button:hover { border-color: #116b5b; }
        .zubu-banner {
            border-bottom: 1px solid #dde6e2;
            padding: 0 0 1.25rem; margin-bottom: 1.5rem;
        }
        .zubu-banner h2 { color: #18332f; margin: 0; font-size: 1.35rem; }
        .zubu-banner p { color: #526b64; margin: .4rem 0 0; font-size: .95rem; }
        .zubu-sidebar-title { color: #116b5b; font-weight: 750; font-size: 1.5rem; }
        [data-testid="stCaptionContainer"] { color: #526b64; }
        [data-testid="stChatMessage"] {
            background: #fff; color: #18332f;
            border-radius: 12px; border: 1px solid #dde6e2;
            padding: 1rem; margin-bottom: .75rem;
        }
        [data-testid="stBottom"], [data-testid="stBottomBlockContainer"] {
            background: #f4f7f6;
        }
        [data-testid="stBottomBlockContainer"] { max-width: 1120px; margin: auto; }
        [data-testid="stChatInput"] {
            background: #fff; border: 1px solid #b8cdc3; border-radius: 12px;
        }
        [data-testid="stChatInput"] textarea { color: #18332f; caret-color: #116b5b; }
        [data-testid="stChatInput"] textarea::placeholder { color: #526b64; opacity: 1; }
        [data-testid="stExpander"] { background: #fff; border-radius: 8px; }
        ::selection { background: #c9e4d9; color: #18332f; }
        @media (max-width: 720px) {
            [data-testid="stMainBlockContainer"] { padding: 1rem 1rem 3rem; }
            .zubu-banner h2 { font-size: 1.15rem; }
        }
    </style>
    """, unsafe_allow_html=True)


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


    with st.sidebar:
        st.markdown('<span class="zubu-sidebar-title">Zubumafu</span>', unsafe_allow_html=True)
        st.caption("Empório da Música")
        if st.button("Nova conversa", key="new_chat", type="primary", use_container_width=True):
            switch_chat(store.create())
            st.rerun()

        st.markdown("#### Minhas conversas")
        st.caption("Exemplos registrados para avaliação")
        for example in EXAMPLES:
            if st.button(example.title, key=f"recorded_{example.key}", use_container_width=True,
                         type="primary" if st.session_state.get("recorded_example") == example.key else "secondary"):
                st.session_state.recorded_example = example.key
                st.session_state.confirm_delete = False
                st.session_state.pop("queued_question", None)
                st.rerun()

        chats = store.list_all()
        personal_chats = [item for item in chats if item["kind"] == "personal"]
        st.caption("Suas conversas")
        if not personal_chats:
            st.caption("Comece uma conversa para vê-la aqui.")
        for item in personal_chats:
            if st.button(strip_emojis(item['title']), key=f"chat_{item['id']}",
                         use_container_width=True,
                         type="primary" if item["id"] == st.session_state.chat_id and not st.session_state.get("recorded_example") else "secondary"):
                switch_chat(item["id"])
                st.rerun()

        st.markdown("#### Conversas de teste")
        for item in (entry for entry in chats if entry["kind"] == "test"):
            if st.button(strip_emojis(item['title']), key=f"test_chat_{item['id']}", use_container_width=True,
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
        st.subheader(("Teste · " if scenario else "") + strip_emojis(conversation["title"]))
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
            st.markdown(strip_emojis(message["content"]))
            show_trace(message.get("trace"))

    question = st.chat_input("Escreva sua mensagem para o Zubumafu...")
    queued = st.session_state.pop("queued_question", None)
    question = question or queued
    if question:
        prior = [{"role": item["role"], "content": item["content"]} for item in messages]
        with st.chat_message("Você", avatar=":material/person:"):
            st.markdown(strip_emojis(question))
        with st.chat_message("Zubumafu", avatar=":material/graphic_eq:"):
            with st.spinner("Zubumafu está consultando as informações..."):
                try:
                    answer, trace = respond(question, history=prior)
                except Exception:
                    logger.exception("Unable to complete the chat request")
                    answer, trace = (
                        "Não consegui acessar o modelo local agora. Confira o Ollama e tente novamente.", []
                    )
            answer = strip_emojis(answer)
            st.markdown(answer)
        try:
            store.add_exchange(st.session_state.chat_id, question, answer, trace)
        except (sqlite3.Error, OSError):
            st.error("A resposta foi exibida, mas não consegui salvar esta conversa no histórico local.")
            st.stop()
        st.rerun()
