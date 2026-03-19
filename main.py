import streamlit as st
from openai import OpenAI
from gtts import gTTS
from pydub import AudioSegment
import speech_recognition as sr
import os
import tempfile
import json
from dotenv import load_dotenv
import uuid

load_dotenv()
OPEN_API_KEY = os.getenv('OPENAI_API_KEY')
client = OpenAI(api_key = OPEN_API_KEY)

st.title("🎤 AI & 데이터분석 면접 코치(실전 모드)")
st.set_page_config(page_title="AI 면접 코치", layout="centered")

# -------------------------
# 상태 초기화
# -------------------------
if "questions" not in st.session_state:
    st.session_state.questions = []

if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0

if "step" not in st.session_state:
    st.session_state.step = "init"

if "current_answer" not in st.session_state:
    st.session_state.current_answer = ""

# -------------------------
# 1. 직무 입력
# -------------------------
job = st.text_input("지원 직무", "데이터분석 & LLM 서비스 개발자")

# -------------------------
# 2. 면접 시작
# -------------------------
if st.button("면접 시작"):

    system_instruction = '당신은 아주 깔끔하고 꼼꼼한 데이터분석을 수행하는 회사의 부사장이야, 아주 친절하고 어드바이스를 잘해주는 마음넓은 임원이야' # 지시 어조
    user_message = f'{job} 직무에 대한 2차 임원 면접에서 나올 질문을 3개를 생각해서 상투적인 (ex 알겠습니다.)말은 제외하고 면접관의 말투처럼 바로 질문을 ,로 구분해서 출력해줘' # 최종적인 질의
    response = client.chat.completions.create(
        model = 'gpt-4.1-mini',
        messages = [{
            'role':'system',
            'content' : [{
                'type':'text',
                'text':system_instruction
            }]},
        {
            'role':'user',
            'content' : [{
                'type':'text',
                'text':user_message
            }]}
        ],
        
        response_format = {'type':'text'},
        temperature = 1.0, 
        top_p = 1,
        max_tokens = 2048, # 응답용 최대 토큰 수
        frequency_penalty = 0, # 출력 토큰 빈도 제약
        presence_penalty = 0 # 출력 토큰 재사용 제약
    )

    st.session_state.questions = response.choices[0].message.content.split(",")
    st.session_state.current_idx = 0
    st.session_state.step = "answer"

# -------------------------
# 3. 질문 + 음성 출력
# -------------------------
if st.session_state.step == "answer":

    idx = st.session_state.current_idx
    question = st.session_state.questions[idx]

    st.subheader(f"📌 질문 {idx+1}")
    st.write(question)

    # 🔊 질문 TTS
    tts = gTTS(text=question, lang='ko')
    file_path = f"q_{idx}.mp3"
    tts.save(file_path)
    st.audio(file_path)

    # -------------------------
    # 🎤 음성 입력
    # -------------------------
    audio_file = st.audio_input("답변을 녹음하세요")

    if audio_file is not None:

        st.audio(audio_file)

        filename = f"{uuid.uuid4()}.wav"

        with open(filename, "wb") as f:
            f.write(audio_file.read())

        # 🔥 Whisper STT
        with open(filename, "rb") as f:
            transcript = client.audio.transcriptions.create(
                model="gpt-4o-mini-transcribe",
                file=f
            )

        text = transcript.text

        st.write("📝 변환된 답변:")
        st.write(text)

        st.session_state.current_answer = text

        if st.button("답변 제출"):
            st.session_state.step = "feedback"

# -------------------------
# 4. 피드백 생성
# -------------------------
if st.session_state.step == "feedback":

    st.subheader("📊 피드백")

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": """
                당신은 아주 꼼꼼한 임원이다.

                아래 기준으로 피드백 작성:
                1. 논리 구조
                2. 데이터 기반 사고
                3. 커뮤니케이션
                4. 개선 방향

                JSON:
                {"feedback": ["", "", "", ""]}
                """
            },
            {
                "role": "user",
                "content": st.session_state.current_answer
            }
        ],

        response_format={"type": "json_object"},
        temperature=1,  # 🔥 안정성 위해 낮춤
        max_tokens=1024
    )

    data = json.loads(response.choices[0].message.content)
    feedbacks = data["feedback"]

    for i, fb in enumerate(feedbacks):
        st.write(f"- {fb}")

        # 🔊 피드백 TTS
        tts = gTTS(text=fb, lang='ko')
        file_path = f"fb_{i}.mp3"
        tts.save(file_path)
        st.audio(file_path)

    # -------------------------
    # 다음 질문
    # -------------------------
    if st.button("다음 질문"):

        st.session_state.current_idx += 1

        if st.session_state.current_idx >= len(st.session_state.questions):
            st.success("🎉 면접 종료!")
            st.session_state.step = "init"
        else:
            st.session_state.step = "answer"