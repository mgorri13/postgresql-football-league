from pathlib import Path

from dotenv import load_dotenv
from langchain_openai import ChatOpenAI


load_dotenv(Path(__file__).with_name(".env"))

llm = ChatOpenAI(model="gpt-5.6-terra")

response = llm.invoke(
    "Reply with exactly: LLM connection successful."
)

print(response.text)