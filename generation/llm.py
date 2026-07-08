from groq import Groq
import os
from dotenv import load_dotenv
from generation.system_promt import prompt

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def llm_response(question, data):
    message = [
        {
            "role" : "system",
            "content": f"This is system prompt --->>> {prompt}, and this is the content related to user question --->>> {data}" 
        },
        {
            "role": "user",
            "content": question
        }
    ]

    response = groq_client.chat.completions.create(
        model=os.getenv("GROQ_MODEL"),
        messages=message,
        temperature=0
    )
    message_llm = response.choices[0].message
    answer = message_llm.content
    return answer