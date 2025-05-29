import os
from datetime import date
from typing_extensions import Annotated

from langchain_core.tools import tool
from langgraph.graph import MessagesState
from langgraph.prebuilt import InjectedState
from langchain_openai import OpenAIEmbeddings
from langchain_core.runnables import RunnableConfig
from langchain_postgres.vectorstores import PGVector

from airbnb_scrapper import initialize_airbnb_scraper


@tool
def retrieve_availability_and_prices(
    check_in: date,
    check_out: date,
    config: RunnableConfig,
    state: Annotated[MessagesState, InjectedState],
    guests: int = 1,
    adults: int = 1,
) -> str:
    """Retrieve availability and prices for a given date range and number of guests."""
    return initialize_airbnb_scraper(
        check_in=check_in.strftime("%Y-%m-%d"),
        check_out=check_out.strftime("%Y-%m-%d"),
        adults=adults,
        config=config,
    )


@tool()
def look_for_information_that_i_don_t_know(
    raw_input: str,
    config: RunnableConfig,
    state: Annotated[MessagesState, InjectedState],
) -> list:
    """Search for information in the knowledge base that the agent does not know.

    Args:
        raw_input (str): The input query to search for.
        thread_id (str): The ID of the conversation thread.
    """

    metadata = config.get("metadata", {})
    thread_id = metadata.get("thread_id")

    vector_store = PGVector(
        embeddings=OpenAIEmbeddings(model="text-embedding-3-large"),
        collection_name="knowledge",
        connection=os.getenv("POSTGRES_URL", ""),
        use_jsonb=True,
    )

    results = vector_store.similarity_search(query=raw_input, k=1, filter={})

    return results
