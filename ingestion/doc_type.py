from groq import Groq
import os
from dotenv import load_dotenv
from generation.system_promt import small_llm

load_dotenv()

groq_client = Groq(api_key=os.getenv('GROQ_API_KEY'))

async def classify_doc_type(first_page_text: str) -> str:

    response = groq_client.chat.completions.create(
        model=os.getenv("GROQ_MODEL"),
        messages=[
            {"role": "system", "content":small_llm},
            {"role": "user", "content": first_page_text[:1500]}
        ],
        temperature=0
    )

    return response.choices[0].message.content.strip()