from typing import List
from fastapi import FastAPI, UploadFile, File
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage, AIMessage, SystemMessage
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate
from langchain_core.output_parsers import JsonOutputParser
import langchain_core.pydantic_v1 as pyd1
import pydantic as pyd2
from openai import OpenAI
import os
import json
import prompt_collection


with open('secrets.json','r') as f:
    API_KEY = json.load(f)
os.environ["OPENAI_API_KEY"] = API_KEY['OPENAI_API_KEY']
client = OpenAI()
model = ChatOpenAI(model="gpt-4-1106-preview", temperature=1.0)

app = FastAPI()

class TtsInfo(pyd2.BaseModel):
    voice: str = pyd2.Field(description="voice")
    input: str = pyd2.Field(description="bot output")
    speech_file_path: str = pyd2.Field(description="file path to save")

class Turn(pyd2.BaseModel):
    role: str = pyd2.Field(description="role")
    content: str = pyd2.Field(description="content")

class Messages(pyd2.BaseModel):
    messages: List[Turn] = pyd2.Field(description="message", default=[])

class Goal(pyd1.BaseModel):
    goal: str = pyd1.Field(description="goal.")
    goal_number: int = pyd1.Field(description="goal number.")
    accomplished: bool = pyd1.Field(description="true if goal is accomplished else false.")

class Goals(pyd1.BaseModel):
    goal_list: List[Goal] = pyd1.Field(default=[])

parser = JsonOutputParser(pydantic_object=Goals)
format_instruction = parser.get_format_instructions()

type_to_msg_class_map = {
    "system": SystemMessage,
    "user": HumanMessage,
    "assistant": AIMessage,
}

roleplay_to_system_prompt_map = prompt_collection.roleplay_to_system_prompt_map
feedback_system_prompt_map = prompt_collection.feedback_system_prompt_map
roleplay_for_opic_to_system_prompt_map = prompt_collection.roleplay_for_opic_to_system_prompt_map

def chat(messages):
    messages_lc = []
    for msg in messages:
        msg_class = type_to_msg_class_map[msg["role"]]
        msg_lc = msg_class(content=msg["content"])
        messages_lc.append(msg_lc)
    resp = model.invoke(messages_lc)
    return {"role": "assistant", "content": resp.content}

@app.post("/chat", response_model=Turn)
def post_chat(messages: Messages):
    # messages -> {"messages": [{"role":"user", "content":"hi"}]}
    print(messages) # messages=[Turn(role='user', content='hi')]
    messages_dict = messages.model_dump()
    print(messages_dict) # {'messages': [{'role': 'user', 'content': 'hi'}]}
    resp = chat(messages=messages_dict['messages'])
    return resp

# Feed Back Chat API
@app.post("/chat/feedback/{feedback}", response_model=Turn)
def post_chat_feed_back(messages: Messages, feedback: str):
    messages_dict = messages.model_dump()
    system_prompt = feedback_system_prompt_map[feedback]
    msgs = messages_dict['messages']
    msgs = [{"role": "system", "content": system_prompt}] + msgs
    resp = chat(messages=msgs)
    return resp

@app.post("/chat/{roleplay}", response_model=Turn)
def post_chat_role_play(messages: Messages, roleplay: str):
    messages_dict = messages.model_dump()
    # 해당 롤플레이를 위한 system prompt 가져오기
    system_prompt = roleplay_to_system_prompt_map[roleplay]
    msgs = messages_dict['messages']
    msgs = [{"role": "system", "content": system_prompt}] + msgs
    resp = chat(messages=msgs)
    return resp

@app.post("/transcribe")
def transcribe_audio(audio_file: UploadFile = File(...)):
    try:
        file_name = "tmp_audio_file.wav"
        with open(file_name, "wb") as f:
            f.write(audio_file.file.read())
        with open(file_name, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                language="en",
            )
        text = transcript.text
    except Exception as e:
        print(e)
        text = f"음성인식에서 실패했습니다. {e}"
        return {"status": "fail", "text": text}
    print(f"input: {text}")
    return {"status": "ok", "text": text}

@app.post("/tts")
def tts_audio_create(bot_info: TtsInfo):
    try:
        bot_info_dict = bot_info.model_dump()
        bot_voice = bot_info_dict["voice"]
        bot_output = bot_info_dict["input"]
        speech_file_path = bot_info_dict["speech_file_path"]
        print(bot_output,bot_voice)
        response = client.audio.speech.create(
            model="tts-1",
            voice=bot_voice,  # alloy, echo, fable, onyx, nova, and shimmer
            input=bot_output
        )
        # speech_file_path = "tmp_speak.mp3"
        response.stream_to_file(speech_file_path)
    except Exception as e:
        print(e)
        text = f"오디오 파일 생성 실패. {e}"
        return {"status": "fail","text":text}
    return {"status": "ok", "text": bot_info_dict}

class ConversationInfo(pyd2.BaseModel):
    conversation: str = pyd2.Field(description="conversation")

@app.post("/speaking_result")
def get_speaking__debate_result(conversation: ConversationInfo):
    model = ChatOpenAI(model="gpt-4-1106-preview")
    conversation_dict = conversation.model_dump()
    conversation_ = conversation_dict['conversation']
    class Score(BaseModel):
        reason: str = Field(description="주어진 대화에 대해 User가 얼마나 논리적이고 유창하게 영어로 응답하였는지 추론하라. 영어로.")
        score: int = Field(description="주어진 대화에서 User의 응답에 대해 유창성과 논리성을 고려하여 0~10점 사이의 점수를 부여하라.")
        improved: str = Field(description="주어진 대화에서 User의 응답보다 더 유창하고 논리적인 모범이 되는 영어문장을 제시하라. 단, 가능한 사람들이 자주 사용하는 쉬운 단어를 사용하라.")

    parser = JsonOutputParser(pydantic_object=Score)
    format_instruction = parser.get_format_instructions()
    human_msg_prompt_template = HumanMessagePromptTemplate.from_template(
        "{input}\n---\n주어진 대화에서 User의 응답에 대해 유창성과 논리성을 고려하여 0~10점 사이의 점수를 부여하라. 다음의 포맷에 맞춰 응답해라.  : {format_instruction}",
        partial_variables={"format_instruction": format_instruction})
    prompt_template = ChatPromptTemplate.from_messages(
        [
            human_msg_prompt_template
        ],
    )
    chain = prompt_template | model | parser
    result = chain.invoke({"input": conversation_,"format_instruction":format_instruction})
    return result