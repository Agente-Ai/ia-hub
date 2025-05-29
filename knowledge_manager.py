import os
import sys
from typing import List
from langchain_openai import OpenAIEmbeddings
from langchain_postgres.vectorstores import PGVector


def __load_documents_to_knowledge_base(
    owner_id: str,
    documents: List[str],
    embedding_model: str = "text-embedding-3-large",
    use_jsonb: bool = True,
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


def __parse_owner_id_from_argv():
    """
    Busca o parâmetro --owner_id=xxxxxx na linha de comando.
    """
    for arg in sys.argv:
        if arg.startswith("--owner_id="):
            return arg.split("=", 1)[1]
    return None


if __name__ == "__main__":
    owner_id_from_argv = __parse_owner_id_from_argv()
    __load_documents_to_knowledge_base(
        owner_id=owner_id_from_argv,
        documents=["Possuimos 7 travesseiros por cada quarto."],
    )
    print(f"Documentos de exemplo carregados para owner_id={owner_id_from_argv}.")
