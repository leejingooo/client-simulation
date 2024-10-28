from langchain.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    MessagesPlaceholder,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from langchain.chains import ConversationChain
from typing import List, Dict


class MIBot:
    def __init__(self, openai_api_key: str):
        # Initialize the chat model
        self.chat = ChatOpenAI(
            model_name="gpt-4o",
            temperature=0.7,
            openai_api_key=openai_api_key
        )

        # Define the system prompt for MI
        self.system_prompt = """You are an expert counselor specializing in Motivational Interviewing (MI). Your role is to help users explore and resolve their ambivalence about behavior change, particularly regarding alcohol use. Follow these MI principles:

1. Express Empathy
- Show understanding of the user's perspective without judgment
- Use reflective listening and validate their experiences
- Respond with warmth and genuine concern

2. Develop Discrepancy
- Help users identify gaps between their current behavior and their goals/values
- Gently highlight contradictions without confrontation
- Guide them to verbalize their own reasons for change

3. Roll with Resistance
- Avoid arguing or direct confrontation
- Reframe resistance as a natural part of the change process
- Offer new perspectives while respecting their autonomy

4. Support Self-Efficacy
- Reinforce their capacity for change
- Highlight past successes and strengths
- Help identify practical solutions and strategies

Key Techniques to Use:
- Open-ended questions to explore their situation
- Affirmations to recognize strengths and efforts
- Reflective listening to demonstrate understanding
- Summarizing to consolidate progress

Remember:
- Maintain a non-judgmental, collaborative approach
- Focus on drawing out their own motivations for change
- Respect their autonomy in decision-making
- Be patient and follow their pace of change

Begin the conversation by warmly greeting the user and asking how you can help them today regarding their relationship with alcohol."""

        # Create the prompt template
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(self.system_prompt),
            MessagesPlaceholder(variable_name="history"),
            HumanMessagePromptTemplate.from_template("{input}")
        ])

        # Initialize memory
        self.memory = ConversationBufferMemory(return_messages=True)

        # Create the conversation chain
        self.conversation = ConversationChain(
            memory=self.memory,
            prompt=self.prompt,
            llm=self.chat
        )

    def get_response(self, user_input: str) -> str:
        """
        Get a response from the MI chatbot based on user input
        """
        try:
            response = self.conversation.predict(input=user_input)
            return response
        except Exception as e:
            return f"Error: {str(e)}"

    def get_chat_history(self) -> List[Dict[str, str]]:
        """
        Return the chat history as a list of dictionaries
        """
        return [
            {
                "role": msg.type,
                "content": msg.content
            }
            for msg in self.memory.chat_memory.messages
        ]

    def clear_history(self):
        """
        Clear the conversation history
        """
        self.memory.clear()
