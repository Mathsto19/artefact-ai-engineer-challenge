"""Streamlit presentation layer for the local Zubumafu prototype."""

import logging

import streamlit as st

from zubumafu.agent import respond


logger = logging.getLogger(__name__)


def show_trace(trace):
    if trace:
        with st.expander("Consultas realizadas"):
            for item in trace:
                st.write(f"{item['tool']} — {item['status']} — resultados: {item.get('matches', 'n/a')}")
                if item.get("filters"):
                    st.json({"filters": item["filters"], "source": item.get("source")})


st.set_page_config(page_title="Zubumafu — Empório da Música", page_icon="🎸")
st.title("🎸 Zubumafu")
st.caption("Assistente musical do Empório da Música · Protótipo com dados demonstrativos")
st.info("Primeira etapa funcional: consultas ao catálogo. Pedidos, promoções e políticas ainda não estão disponíveis neste protótipo.")

if "messages" not in st.session_state:
    st.session_state.messages = []

if st.button("Nova conversa"):
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        show_trace(message.get("trace"))

question = st.chat_input("Quer encontrar um instrumento? Me conta!")
if question:
    prior_history = [{"role": item["role"], "content": item["content"]} for item in st.session_state.messages]
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)
    with st.chat_message("assistant"):
        with st.spinner("Zubumafu está pensando na melhor resposta..."):
            try:
                answer, trace = respond(question, prior_history)
            except Exception:
                logger.exception("Unable to complete the chat request")
                answer, trace = "Não consegui concluir a consulta agora. Confira se o Ollama está aberto e tente novamente.", []
        st.markdown(answer)
        show_trace(trace)
    st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace})
