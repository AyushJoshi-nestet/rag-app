from groq import Groq
import os
from dotenv import load_dotenv
from sqlmodel import select
from generation.system_promt import prompt
from storage.data import LLM_Response

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def get_previous_responses(user_email, session, limit=2):
    statement = (
        select(LLM_Response)
        .where(LLM_Response.user_email == user_email)
        .order_by(LLM_Response.created_at.desc())
        .limit(limit)
    )
    records = session.exec(statement).all()
    return records

async def llm_response(question, data, session, user_email):
    previous = get_previous_responses(user_email, session, limit=2)
    
    message = [
        {
            "role": "system",
            "content": f"This is system prompt --->>> {prompt}, and this is the content related to user question --->>> {data}"
        }
    ]

    for record in previous:
    
        message.append({"role": "assistant", "content": f"This is teh previous question asked --->>> {record.question}"})
        message.append({"role": "assistant", "content": f"This is the response to that question --->>> {record.llm_response}"})
    
    message.append({"role": "user", "content": question})

    response = groq_client.chat.completions.create(
    
        model=os.getenv("GROQ_MODEL"),
        messages=message,
        stream=True,
        temperature=0
    )

    database_save = []
    for chunk in response:
        content = chunk.choices[0].delta.content
        if content:
            database_save.append(content)
            yield f"data: {content}\n\n"

    final_response = "".join(database_save)
    new_response = LLM_Response(user_email= user_email, question=question, llm_response=final_response)
    session.add(new_response)
    session.commit()

    #removed teh paddle ocr layer and changed it with the OCRmyPDF and pdfplumber a it was taking longer time for text extraction and 
    
    #applied expiration of the token in which any token will expire after 30 minutes ad have to get teh enew on e after this much time
    
    #passowrd was being saved as simple text and was being exposed in the token fixed it with the passowrd being saved as hash and token being geenrated on email only
