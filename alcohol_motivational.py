from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.schema import HumanMessage, AIMessage
from langchain.callbacks import StreamingStdOutCallbackHandler
from langchain.memory import ConversationBufferMemory


class MITherapist:
    def __init__(self, openai_api_key):
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

        # Define the system prompt for MI therapy
        self.system_prompt = """You are an expert therapist specialized in Motivational Interviewing (MI) for alcohol addiction. 
        Follow these key MI principles in your responses:

        1. Express Empathy:
        - Show deep understanding of the patient's experiences and feelings
        - Use reflective listening
        - Avoid judgment or criticism

        2. Develop Discrepancy:
        - Help patients see the gap between their current behavior and their goals
        - Explore their values and how alcohol use conflicts with these
        
        3. Roll with Resistance:
        - Avoid arguing or direct confrontation
        - Acknowledge ambivalence as normal
        - Reflect back patient's concerns
        
        4. Support Self-Efficacy:
        - Recognize and reinforce patient's strengths
        - Emphasize their ability to change
        - Highlight past successes

        5. Communication Style:
        - Ask open-ended questions
        - Use reflective listening
        - Affirm patient's strengths and efforts
        - Summarize key points regularly

        Always maintain a warm, non-judgmental, and professional tone. Focus on eliciting the patient's own motivations for change rather than imposing your views.

        Start the conversation by introducing yourself briefly and asking an open-ended question about what brings them here today."""

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
