import io
import base64
import requests
import streamlit as st
from audio_recorder_streamlit import audio_recorder
from streamlit_option_menu import option_menu
import opic_section1_collection as op_s1
from langchain.schema import StrOutputParser, AIMessage, HumanMessage, SystemMessage

st.set_page_config(
    page_title="Baduk's 영어회화",
    page_icon="🐶"
)

# Backend API url
host_url = "http://localhost:8000"
chat_url = f"{host_url}/chat"
tts_url = f"{host_url}/tts"
transcribe_url = f"{host_url}/transcribe"
speaking_result_url = f"{host_url}/speaking_result"

# 프리토킹
if "curr_page" not in st.session_state:
    st.session_state["curr_page"] = "프리토킹"
if "messages" not in st.session_state:
    st.session_state.messages = []
if "prev_audio_bytes" not in st.session_state:
    st.session_state.prev_audio_bytes = None
if "prev_audio_bytes_feedback" not in st.session_state:
    st.session_state.prev_audio_bytes_feedback = None
if "prev_user_input" not in st.session_state:
    st.session_state.prev_user_input = None
if "feedback_message" not in st.session_state:
    st.session_state.feedback_message = []
if "grammar_check_list" not in st.session_state:
    st.session_state.grammar_check_list = []
if "prev_feedback_input" not in st.session_state:
    st.session_state.prev_feedback_input = []
if "prev_easy_explain_input" not in st.session_state:
    st.session_state.prev_easy_explain_input = []
if "prev_translate_input" not in st.session_state:
    st.session_state.prev_translate_input = []

# 오픽연습
if "page_number" not in st.session_state:
    st.session_state.page_number = 1
if "exam_context" not in st.session_state:
    st.session_state.exam_context = {'messages':[]}
if "prev_answer" not in st.session_state:
    st.session_state.prev_answer = ""
if "speaking_result" not in st.session_state:
    st.session_state.speaking_result = []
if "default_text_area_input" not in st.session_state:
    st.session_state.default_text_area_input = ""

    ###############################################

# Helpers
def stt(audio_bytes):
    audio_file = io.BytesIO(audio_bytes)
    files = {"audio_file": ("audio.wav", audio_file, "audio/wav")}
    response = requests.post(transcribe_url, files=files)
    return response.json()

def tts(bot_output, voice, speech_file_path):
    response = requests.post(tts_url, json={"voice":voice,"input":bot_output,
                                            "speech_file_path":speech_file_path})
    return response

def chat(text, roleplay):
    user_turn = {"role": "user", "content": text}
    messages = st.session_state.messages + [user_turn]
    #[{"role": "user", "content": text}, {...}, ...]
    resp = requests.post(chat_url + f"/{roleplay}", json={"messages": messages})
    assistant_turn = resp.json()
    return assistant_turn['content']

def chat_for_feedback(text, feedback):
    user_turn = {"role": "user", "content": text}
    messages = st.session_state.feedback_message + [user_turn]
    resp = requests.post(chat_url + f"/feedback/{feedback}", json={"messages": messages})
    assistant_turn = resp.json()
    return assistant_turn['content']

def autoplay_audio(file_path: str):
    with open(file_path, "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f"""
            <audio controls autoplay="true">
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(
            md,
            unsafe_allow_html=True,
        )

def speaking_result(conversation: str):
    resp = requests.post(speaking_result_url, json={"conversation": conversation})
    print(resp.json())
    return resp.json()

###############################################
###############################################
# UI
with st.sidebar:
    # selected = option_menu("Menu", ["프리토킹", '주제토킹', '작문교정', '오픽연습'],
    #     icons=['emoji-smile', 'chat-square-dots','pencil', 'award'], menu_icon="rocket-takeoff", default_index=0)
    # st.session_state["curr_page"] = selected
    #
    selected = option_menu("Menu", ["프리토킹", '오픽연습'],
        icons=['emoji-smile', 'award'], menu_icon="rocket-takeoff", default_index=0)
    st.session_state["curr_page"] = selected

if st.session_state["curr_page"] == "프리토킹":
    st.title(st.session_state["curr_page"])
    # client = OpenAI()
    roleplay = 'kevin'
    # Conversation
    speech_file_path = "tmp_speak.mp3"
    speech_feedback_file_path = "tmp_speak_feedback.mp3"
    with st.container(border=True, height=300):
        con1 = st.container()
        con2 = st.container()

    user_input = ""
    user_input_feedback = ""
    user_input_feedback_chat = ""
    user_input_for_translate = ""
    with con2:  # 마이크 & 채팅창
        audio_bytes = audio_recorder("Click mic", pause_threshold=3.0)
        prompt = st.chat_input("Say something")
        if prompt:
            user_input = prompt
        if audio_bytes == st.session_state.prev_audio_bytes:
            audio_bytes = None
        st.session_state.prev_audio_bytes = audio_bytes
        try:
            if audio_bytes:
                with st.spinner("Loading..."):
                    resp_stt = stt(audio_bytes)
                    print('stt_response', resp_stt['text'])
                    status = resp_stt['status']
                    if status == 'ok':
                        user_input = resp_stt['text']
        except Exception as e:
            print(e)
            pass

    with con1:  # 재생창
        replay = st.button('Replay')
        if replay:
            autoplay_audio(speech_file_path)
        if user_input and st.session_state.prev_user_input != user_input:
            st.session_state.prev_user_input = user_input
            st.session_state.messages.append({"role": "user", "content": user_input})

            with st.chat_message("user"):
                st.markdown(user_input)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    bot_output = chat(user_input, roleplay)
                with st.spinner("Creating audio..."):
                    response = tts(bot_output,"onyx","tmp_speak.mp3")
                    print('tts_response', bot_output)
                    autoplay_audio(speech_file_path)
            st.session_state.messages.append({"role": "assistant", "content": bot_output})

    with st.container(border=True):
        st.markdown("### History")
        with st.expander("Click to see history"):
            for i, message in enumerate(st.session_state.messages):  # 메시지 히스토리
                with st.chat_message(message["role"]):
                    st.markdown(message["content"])
                    if message["role"] == 'user':
                        grammar_check_button_pressed = st.button('Check', key=f"btn_check_{i}")
                        if grammar_check_button_pressed:
                            user_input_feedback = message["content"]
                            feedback_type = 'check_grammar'
                    else:
                        col1, col2 = st.columns([1,5])
                        with col1:
                            explain_button_pressed = st.button('Explain', key=f"btn_explain_{i}")
                            if explain_button_pressed:
                                user_input_feedback = message["content"]
                                feedback_type = 'explain'
                        with col2:
                            Translate_button_pressed = st.button('Translate', key=f"btn_Translate_{i}")
                            if Translate_button_pressed:
                                user_input_for_translate = message["content"]
                                feedback_type = 'translate'

    with st.container(border=True):
        st.markdown("### Feedback AI")
        replay2 = st.button('Replay2')
        if replay2:
            autoplay_audio(speech_feedback_file_path)
        audio_bytes2 = audio_recorder("Click mic2", pause_threshold=3.0)
        if audio_bytes2 == st.session_state.prev_audio_bytes_feedback:
            audio_bytes2 = None
        st.session_state.prev_audio_bytes_feedback = audio_bytes2
        try:
            if audio_bytes2:
                with st.spinner("Loading..."):
                    resp_stt = stt(audio_bytes2)
                    status = resp_stt['status']
                    if status == 'ok':
                        user_input_feedback_chat = resp_stt['text']
        except Exception as e:
            print(e)
            pass

        #Feedback Chat
        prompt_feedback = st.chat_input("Say something (Feedback)")
        if prompt_feedback:
            user_input_feedback_chat = prompt_feedback
        if user_input_feedback_chat and user_input_feedback_chat not in st.session_state.prev_feedback_input:
            st.session_state.prev_feedback_input.append(user_input_feedback_chat)
            st.session_state.grammar_check_list.append({"role": "user", "content": user_input_feedback_chat})
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    bot_output = chat_for_feedback(user_input_feedback_chat, 'feed_back_chat')
                with st.spinner("Creating audio..."):
                    tts(bot_output, "echo", "tmp_speak_feedback.mp3")
                    autoplay_audio(speech_feedback_file_path)
            st.session_state.grammar_check_list.append({"role": "assistant", "content": bot_output})

        #Check
        if user_input_feedback in st.session_state.prev_feedback_input:
            st.error('You alread asked that :)')
        else:
            if user_input_feedback and user_input_feedback not in st.session_state.prev_feedback_input:
                st.session_state.prev_feedback_input.append(user_input_feedback)
                st.session_state.grammar_check_list.append({"role": "user", "content": user_input_feedback})
                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        bot_output = chat_for_feedback(user_input_feedback, feedback_type)
                    with st.spinner("Creating audio..."):
                        tts(bot_output,"echo","tmp_speak_feedback.mp3")
                        autoplay_audio(speech_feedback_file_path)
                st.session_state.grammar_check_list.append({"role": "assistant", "content": bot_output})

        #Translate
        if user_input_for_translate in st.session_state.prev_translate_input:
            st.error('You alread translated that :)')
        if user_input_for_translate and user_input_for_translate not in st.session_state.prev_translate_input:
            st.session_state.prev_translate_input.append(user_input_for_translate)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    bot_output = chat_for_feedback(user_input_for_translate, "translate")
            st.session_state.grammar_check_list.append({"role": "assistant", "content": bot_output})
        with st.expander("Click to see history"):
            for i, grammar_check in enumerate(st.session_state.grammar_check_list):
                with st.chat_message(grammar_check["role"]):
                    st.markdown(grammar_check["content"])
                    # if message["role"] == 'assistant':
                    #     col3, col4 = st.columns([1,5])
                    #     with col3:
                    #         easy_explain_button_pressed = st.button('Easy explain', key=f"btn_easy_explain{i}")
                    #         if easy_explain_button_pressed:
                    #             user_input_feedback = message["content"]
                    #             feedback_type = 'easy_explain'
                    #     with col4:
                    #         Translate_button_pressed = st.button('Translate2', key=f"btn_Translate2_{i}")
                    #         if Translate_button_pressed:
                    #             user_input_for_translate = message["content"]
                    #             feedback_type = 'translate'


# elif st.session_state["curr_page"] == "주제토킹":
#     st.title(st.session_state["curr_page"])
#
# elif st.session_state["curr_page"] == "작문교정":
#     st.title(st.session_state["curr_page"])

elif st.session_state["curr_page"] == "오픽연습":
    st.title(st.session_state["curr_page"])
    section1_topic_list = op_s1.opic_section1
    selected_topic = st.selectbox(
        'What topic would you like to choose?',
        section1_topic_list.keys(),placeholder='Choose a topic')
    if st.session_state.get('option', None) != selected_topic:
        st.session_state['page_number'] = 1
        st.session_state['option'] = selected_topic
        st.session_state['expander_state'] = False

    st.write('You selected:', selected_topic)
    page_number = st.session_state.page_number
    total_page = len(section1_topic_list[selected_topic])

    # 이전 페이지 버튼
    col1, col2 = st.columns([1, 10])
    with col1:
        if st.button("Prev"):
            if page_number > 1:
                page_number -= 1
                st.session_state['page_number'] = page_number
                st.session_state['expander_state'] = False
    with col2:
        # 다음 페이지 버튼
        if st.button("Next"):
            if page_number < total_page:
                page_number += 1
                st.session_state['page_number'] = page_number
                st.session_state['expander_state'] = False
    # 페이지 내용 표시
    st.subheader(f'Q{page_number} / {total_page}')

    expander_state = st.session_state.get('expander_state', False)
    if st.button("Click to see script"):
        expander_state = not expander_state

    st.session_state['expander_state'] = expander_state
    if st.session_state['expander_state']:
        with st.chat_message("user",avatar="🐶"):
            st.markdown(section1_topic_list[selected_topic][page_number-1])

    play = st.button('Listen question')
    if play:
        file_name = selected_topic +"_" +str(page_number) + ".mp3"
        try:
            autoplay_audio("opic_s1/"+file_name)
        except Exception as e:
            print(e)
            with st.spinner("Creating audio..."):
                response = tts(section1_topic_list[selected_topic][page_number - 1], "alloy", "opic_s1/"+file_name)
                print('tts_response', section1_topic_list[selected_topic][page_number - 1])
                autoplay_audio("opic_s1/"+file_name)

    ## Input text
    default_text_area_input = st.session_state.default_text_area_input
    txt = st.text_area(
        "Your answer",default_text_area_input,
        height=200,
        placeholder = "Write your answer here"
    )
    st.session_state.default_text_area_input = txt
    submit_button = st.button("Submit / Replay", type="primary")
    user_input = ""
    file_name = selected_topic + "_" + str(page_number) + "_feedback" + ".mp3"
    if submit_button:
        if len(txt)>0:
            user_input = txt
            if user_input == st.session_state.prev_answer:
                autoplay_audio("opic_s1_feedback/" + file_name)
            else:
                st.toast('Your answer has been submitted !', icon='👏🏻')
        else:
            st.error('You should write answer 🧚‍')

    if user_input and user_input != st.session_state.prev_answer:
        st.session_state.exam_context['messages'] = []
        st.session_state.prev_answer = user_input
        st.session_state.exam_context['messages'].append(
            AIMessage(content=section1_topic_list[selected_topic][page_number - 1]))
        st.session_state.exam_context['messages'].append(HumanMessage(content=user_input))
        conversation = ""
        for msg in st.session_state.exam_context["messages"]:
            role = 'User' if msg.type == 'human' else 'AI'
            conversation += f"{role}: {msg.content}"

        with st.spinner("Thinking..."):
            result = speaking_result(conversation)
        with st.spinner("Creating audio..."):

            reason_and_improved = result['reason'] + "\n\nImproved sentence below\n\n" + result['improved']
            response = tts(reason_and_improved, "onyx", "opic_s1_feedback/" + file_name)
        st.session_state.speaking_result.append(reason_and_improved)
        autoplay_audio("opic_s1_feedback/" + file_name)

    expander_state2 = st.session_state.get('expander_state2', False)
    if st.button("Click to see feedback"):
        expander_state2 = not expander_state2
    st.session_state['expander_state2'] = expander_state2
    if st.session_state['expander_state2']:
        for re in st.session_state.speaking_result:
            with st.chat_message("user", avatar="👩‍🏫"):
                st.markdown(re)