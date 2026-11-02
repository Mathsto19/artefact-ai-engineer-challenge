"""Streamlit presentation layer for the local Zubumafu prototype."""

import streamlit as st

from zubumafu.agent import respond


st.set_page_config(page_title="Zubumafu — Empório da Música", page_icon="🎸")
st.title("🎸 Zubumafu")
st.caption("Assistente musical do Empório da Música · Protótipo com dados demonstrativos")
st.info("Primeira etapa funcional: consultas ao catálogo. Pedidos, promoções e políticas ainda não estão disponíveis neste protótipo.")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        if message.get("trace"):
            with st.expander("Consultas realizadas"):
                for item in message["trace"]:
                    st.write(f"{item['tool']} — {item['status']} — resultados: {item.get('matches', 'n/a')}")

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
                answer, trace = "Não consegui acessar o modelo local agora. Confira se o Ollama está aberto e tente novamente.", []
        st.markdown(answer)
        if trace:
            with st.expander("Consultas realizadas"):
                for item in trace:
                    st.write(f"{item['tool']} — {item['status']} — resultados: {item.get('matches', 'n/a')}")
    st.session_state.messages.append({"role": "assistant", "content": answer, "trace": trace})
