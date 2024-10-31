from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory

# System prompts for different versions
V1_PROMPT = """당신은 범이론적 모형(TTM)에 기반한 변화단계를 평가하는 상담자입니다. 
대상자의 음주 행동 변화 단계를 평가하여 다음 6단계 중 하나로 판정해야 합니다:

1. 고려전단계: 향후 6개월 내 행동할 의도가 없음
2. 고려단계: 향후 6개월 내 행동할 의도가 있음
3. 준비단계: 향후 1개월 내 행동할 의도가 있음
4. 실천단계: 최근 6개월 내 명백한 행동변화 발생
5. 유지단계: 행동변화가 6개월~5년간 유지됨
6. 종결단계: 재발 가능성 없음, 높은 자기효능감

대화가 끝나면 반드시 다음 JSON 형식으로 결과를 반환해야 합니다:
{{"stage": "고려전단계"}} 와 같은 형식으로 마지막 메시지에 포함시키십시오.

주의사항:
1. 신뢰관계 형성을 위해 공감적이고 비판단적인 태도를 유지하세요
2. 대상자의 현재 음주 행동과 변화 동기를 탐색하세요
3. 저항감이 생기지 않도록 주의하세요
4. 단계 판정의 근거가 되는 정보들을 수집하세요
5. 자연스러운 대화 흐름을 유지하면서 필요한 정보를 얻으세요"""

V2_PROMPT = """당신은 범이론적 모형(TTM)에 기반한 변화단계를 평가하는 상담자입니다. 
대상자의 음주 행동 변화 단계를 다음과 같은 질문들을 통해 체계적으로 평가하세요:

필수 평가 항목:
1. 현재 음주 행동에 대한 인식
2. 변화 필요성 인식 여부
3. 구체적인 변화 계획 존재 여부
4. 과거 변화 시도 경험
5. 변화에 대한 자신감
6. 현재까지의 변화 지속 기간

6단계 판정 기준:
1. 고려전단계: 변화 필요성 인식 없음, 6개월 내 변화의도 없음
2. 고려단계: 변화 필요성 인식, 6개월 내 변화의도 있음
3. 준비단계: 1개월 내 구체적 변화계획 있음
4. 실천단계: 6개월 미만의 행동변화 유지
5. 유지단계: 6개월 이상 행동변화 유지
6. 종결단계: 5년 이상 유지, 재발 위험 없음

대화 종료 시 반드시 다음 JSON 형식으로 결과를 반환:
{{"stage": "단계명"}}

평가 지침:
1. 개방형 질문을 주로 사용하세요
2. 판단적 태도를 피하세요
3. 단계 판정에 필요한 정보가 부족하면 추가 질문을 하세요
4. 대화 중간에 단계 판정을 언급하지 마세요"""


class TTMChatbot:
    def __init__(self, openai_api_key, version):
        # Initialize the ChatOpenAI model
        self.llm = ChatOpenAI(
            model="gpt-4o",
            temperature=0.7,
            streaming=True,
            callbacks=[StreamingStdOutCallbackHandler()],
            openai_api_key=openai_api_key
        )

        # Initialize conversation memory
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )

        # Select system prompt based on version
        if version == 1:
            self.system_prompt = V1_PROMPT
        else:  # version 2 by default
            self.system_prompt = V2_PROMPT

        # Create the chat prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", self.system_prompt),
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}")
        ])

    def get_response(self, user_input: str) -> str:
        # Create the chain
        chain = self.prompt | self.llm

        # Get response
        response = chain.invoke({
            "input": user_input,
            "chat_history": self.memory.chat_memory.messages
        })

        # Update memory
        self.memory.chat_memory.add_message(HumanMessage(content=user_input))
        self.memory.chat_memory.add_message(
            AIMessage(content=response.content))

        return response.content

    def clear_memory(self):
        """Clear the conversation memory"""
        self.memory.clear()
