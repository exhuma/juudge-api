import logging

from langchain.chains import create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableBinding
from langchain_openai import ChatOpenAI
from langchain_postgres import PGVector

LOG = logging.getLogger(__name__)


def create_chain(vectorstore: PGVector) -> RunnableBinding:
    model = ChatOpenAI(model="gpt-4")
    retriever = vectorstore.as_retriever()
    system_prompt = (
        'you are an expert in "magic: the gathering" and you are asked to answer a '
        "question about the game. Your answers are consise an take extra care "
        "about rulings of the cards. "
        "Use the following pieces of retrieved context to answer "
        "the question. If you don't know the answer, say that you "
        "don't know."
        "\n\n"
        "{context}"
    )

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system_prompt),
            ("human", "{input}"),
        ]
    )

    question_answer_chain = create_stuff_documents_chain(model, prompt)
    rag_chain = create_retrieval_chain(retriever, question_answer_chain)
    return rag_chain


def query(rag_chain: RunnableBinding, question: str):
    response = rag_chain.invoke({"input": question})
    return response
