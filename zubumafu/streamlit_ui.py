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


def main() -> None:
    st.set_page_config(page_title="Zubumafu | Empório da Música", page_icon="🎸", layout="wide")

    st.markdown("""
    <style>
        :root { --zubu-green: #075e54; --zubu-mint: #d9f8e8; --zubu-bg: #e7eee9; }
        .stApp { background: var(--zubu-bg); }
        [data-testid="stSidebar"] { background: #f8fbf9; border-right: 1px solid #d6e1dd; }
        [data-testid="stSidebar"] .stButton > button {
            border-radius: 12px; justify-content: flex-start;
            border-color: #e0e8e5; text-align: left;
        }
        .zubu-banner {
            background: linear-gradient(110deg, #075e54, #128c7e);
            padding: 19px 24px; border-radius: 16px; color: white;
            margin-bottom: 14px; box-shadow: 0 3px 12px #075e541c;
        }
        .zubu-banner h2 { color: white !important; margin: 0; font-size: 1.45rem; }
        .zubu-banner p { color: #e4f4ee; margin: 5px 0 0; font-size: .88rem; }
        .zubu-sidebar-title { color: #075e54; font-weight: 800; font-size: 1.3rem; }
        [data-testid="stChatMessage"] { border-radius: 15px; border: 1px solid #e2e8e4; padding: 11px 15px; }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) {
            background: var(--zubu-mint); margin-left: 13%;
        }
        [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) {
            background: #fff; margin-right: 13%;
        }
        [data-testid="stChatInput"] { border-radius: 16px; }
        @media (max-width: 720px) {
            [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) { margin-left: 4%; }
            [data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]) { margin-right: 4%; }
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
        st.session_state.confirm_delete = False
        st.session_state.pop("queued_question", None)


    with st.sidebar:
        st.markdown('<span class="zubu-sidebar-title">🎸 Zubumafu</span>', unsafe_allow_html=True)
        st.caption("Suas conversas ficam neste computador.")
        if st.button("＋ Nova conversa", key="new_chat", type="primary", use_container_width=True):
            switch_chat(store.create())
            st.rerun()

        st.markdown("#### 💬 Minhas conversas")
        chats = store.list_all()
        personal_chats = [item for item in chats if item["kind"] == "personal"]
        if not personal_chats:
            st.caption("Comece uma conversa para vê-la aqui.")
        for item in personal_chats:
            if st.button(f"💬 {item['title']}", key=f"chat_{item['id']}",
                         use_container_width=True,
                         type="primary" if item["id"] == st.session_state.chat_id else "secondary"):
                switch_chat(item["id"])
                st.rerun()

        st.markdown("#### 🧪 Conversas de teste")
        st.caption("Roteiros executados com o modelo local, não respostas prontas.")
        for item in (entry for entry in chats if entry["kind"] == "test"):
            if st.button(f"🧪 {item['title']}", key=f"test_chat_{item['id']}", use_container_width=True,
                         type="primary" if item["id"] == st.session_state.chat_id else "secondary"):
                switch_chat(item["id"])
                st.rerun()
        with st.expander("＋ Iniciar um roteiro de validação"):
            for scenario in SCENARIOS:
                if st.button(scenario.title, key=f"new_scenario_{scenario.key}", use_container_width=True):
                    switch_chat(store.create(kind="test", scenario_id=scenario.key,
                                             title=scenario.title))
                    st.rerun()

        st.divider()
        st.caption("Protótipo local · Não conectado ao WhatsApp · Sem autenticação de produção")
        st.caption("Atenção: as mensagens, inclusive e-mails digitados, ficam neste computador em um arquivo local sem criptografia. Exclua conversas sensíveis quando terminar.")


    conversation = store.get(st.session_state.chat_id)
    scenario = SCENARIO_BY_KEY.get(conversation["scenario_id"]) if conversation["kind"] == "test" else None
    st.markdown("""
    <div class="zubu-banner">
      <h2>🎸 Zubumafu <small style="font-size:.72rem;font-weight:400">· modelo local</small></h2>
      <p>Empório da Música · Atendimento musical com dados demonstrativos</p>
    </div>
    """, unsafe_allow_html=True)
    header, remove_column = st.columns([8, 2], vertical_alignment="center")
    with header:
        st.subheader(("🧪 Teste · " if scenario else "💬 ") + conversation["title"])
        if scenario:
            st.caption("Cenário de validação: respostas reais só aparecem após executar a pergunta.")
        else:
            st.caption("Histórico pessoal salvo localmente; selecione outra conversa sem perder esta.")
    with remove_column:
        if st.button("🗑 Excluir", key="delete_chat", use_container_width=True):
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
        with st.expander("🧪 Perguntas e critérios deste teste", expanded=True):
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
        st.info("Uma conversa novinha. Pergunte sobre instrumentos, políticas, preços ou pedidos. 🙂")
    for message in messages:
        with st.chat_message(message["role"], avatar="🎸" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])
            show_trace(message.get("trace"))

    question = st.chat_input("Escreva sua mensagem para o Zubumafu...")
    queued = st.session_state.pop("queued_question", None)
    question = question or queued
    if question:
        prior = [{"role": item["role"], "content": item["content"]} for item in messages]
        with st.chat_message("user", avatar="👤"):
            st.markdown(question)
        with st.chat_message("assistant", avatar="🎸"):
            with st.spinner("Zubumafu está consultando as informações..."):
                try:
                    answer, trace = respond(question, history=prior)
                except Exception:
                    logger.exception("Unable to complete the chat request")
                    answer, trace = (
                        "Não consegui acessar o modelo local agora. Confira o Ollama e tente novamente.", []
                    )
            st.markdown(answer)
        try:
            store.add_exchange(st.session_state.chat_id, question, answer, trace)
        except (sqlite3.Error, OSError):
            st.error("A resposta foi exibida, mas não consegui salvar esta conversa no histórico local.")
            st.stop()
        st.rerun()
