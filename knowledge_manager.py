import os
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector


def load_documents_to_knowledge_base(
    documents: List[str],
    embedding_model: str = "text-embedding-3-large",
    use_jsonb: bool = True,
    owner_id: str = None,
) -> None:
    """
    Carrega uma lista de documentos (strings) na base de conhecimento (tabela knowledge)
    usando LangChain e PGVector, registrando um identificador nos metadados.
    """
    vector_store = PGVector(
        embeddings=OpenAIEmbeddings(model=embedding_model),
        connection=os.getenv("POSTGRES_URL", ""),
        use_jsonb=use_jsonb,
    )

    metadatas = [{"owner_id": owner_id} for _ in documents]

    vector_store.add_texts(documents, metadatas=metadatas)


def load_example_documents():
    """
    Exemplo de uso: carrega documentos de exemplo na base de conhecimento.
    """
    example_docs = [
        "Possuimos 7 travesseiros por cada quarto.",
    ]

    load_documents_to_knowledge_base(example_docs, owner_id="default_owner")


if __name__ == "__main__":
    load_example_documents()
    print("Documentos de exemplo carregados na base de conhecimento.")
