from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory


class TTMChatbot:
    def __init__(self, openai_api_key):
        self.chat = ChatOpenAI(
            temperature=0.7,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            openai_api_key=openai_api_key
        )

        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="history"
        )

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """당신은 내담자의 변화단계를 평가하는 전문가입니다.
            범이론적 모형(TTM)의 6단계(전숙고, 숙고, 준비, 실행, 유지, 종결)에 따라
            내담자의 음주 행동 변화 단계를 평가해야 합니다.

            평가 규칙:
            1. 한 번에 하나의 질문만 하세요.
            2. 내담자의 응답을 바탕으로 다음 질문을 선택하세요.
            3. 충분한 정보가 모이면 6단계 중 하나로 판단하세요.
            4. 판단이 끝나면 다음 형식으로 반환하세요: <STAGE>단계명</STAGE>

            주요 평가 포인트:
            - 향후 6개월 내 변화 의도
            - 향후 1개월 내 실천 계획
            - 실제 행동 변화 여부
            - 변화 지속 기간
            - 재발 가능성

            대화는 공감적이고 지지적인 톤을 유지하되, 판단적이지 않아야 합니다."""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}")
        ])

        self.conversation_started = False

    def get_stage(self, user_input: str) -> dict:

        if not self.conversation_started:
            self.conversation_started = True
            first_message = "안녕하세요. 오늘 음주 행동 변화에 대해 이야기를 나눠보려고 합니다. 현재 음주가 걱정되거나 변화가 필요하다고 생각하시나요?"
            return {"stage": None, "message": first_message}

        # 사용자 입력을 메모리에 저장
        self.memory.chat_memory.add_human_message(user_input)

        # 프롬프트 포맷팅
        messages = self.prompt.format_messages(
            history=self.memory.chat_memory.messages,
            input=user_input
        )

        # 챗봇 응답 생성
        response = self.chat.invoke(messages)

        # AI 응답을 메모리에 저장
        self.memory.chat_memory.add_ai_message(response.content)

        # 변화단계가 결정되었는지 확인
        if "<STAGE>" in response.content and "</STAGE>" in response.content:
            start = response.content.find("<STAGE>") + 7
            end = response.content.find("</STAGE>")
            stage = response.content[start:end]
            return {"stage": stage, "message": response.content}

        return {"stage": None, "message": response.content}
