from groq import Groq
import os
from dotenv import load_dotenv
from sqlmodel import select
from generation.system_promt import prompt
from storage.data import LLM_Response

load_dotenv()

groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))


def get_previous_responses(document_id, session, limit=2):
    statement = (
        select(LLM_Response)
        .where(LLM_Response.document_id == document_id)
        .order_by(LLM_Response.created_at.desc())
        .limit(limit)
    )
    records = session.exec(statement).all()
    return records


async def llm_response(question, data, session, document_id):

    previous = get_previous_responses(document_id, session, limit=2)
    print(data)

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
    new_response = LLM_Response(document_id=document_id, question=question, llm_response=final_response)
    session.add(new_response)
    session.commit()