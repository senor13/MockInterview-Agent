import os
from langfuse.openai import OpenAI
from dotenv import load_dotenv
from config import INTERVIEWER_MODEL
import instructor

load_dotenv()

client = OpenAI(api_key = os.environ["OPENAI_API_KEY"])
instructor_client = instructor.from_openai(client)
def call_llm(messages,tools = None,response_model = None):
    kwargs = {"model" : INTERVIEWER_MODEL, "messages" : messages}
    if tools:
        kwargs["tools"] = tools
    if response_model:
        kwargs["response_model"] = response_model
        response = instructor_client.chat.completions.create(**kwargs)
        return response
    else:
        response = client.chat.completions.create(**kwargs)
        return response.choices[0].message
