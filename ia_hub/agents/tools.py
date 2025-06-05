import os
from datetime import date

from langchain_core.tools import tool
from langchain_openai import OpenAIEmbeddings
from langchain_core.runnables import RunnableConfig
from langchain_postgres.vectorstores import PGVector

from ..airbnb.airbnb_scrapper import initialize_airbnb_scraper


@tool()
def retrieve_availability_and_prices(
    check_in: date,
    check_out: date,
    guests: int,
    adults: int,
    config: RunnableConfig,
) -> str:
    """
    Fetches availability and pricing information for a specified stay period.

    Args:
        check_in (date): The start date of the stay.
        check_out (date): The end date of the stay.
        guests (int): Total number of guests including adults and children.
        adults (int): Number of adult guests.
        config (RunnableConfig): Configuration options for the execution context.

    Returns:
        str: A formatted string containing availability status and price details
             for the given date range and guest configuration.
    """
    return initialize_airbnb_scraper(
        check_in=check_in.strftime("%Y-%m-%d"),
        check_out=check_out.strftime("%Y-%m-%d"),
        adults=adults,
        guests=guests,
        config=config,
    )


@tool()
def look_for_information_that_i_don_t_know(
    raw_input: str,
    config: RunnableConfig,
) -> list:
    """
    Searches the knowledge base for information not currently known to the agent.

    Args:
        raw_input (str): The user's query or input text containing the information need.
        config (RunnableConfig): Configuration for the tool's execution context.

    Returns:
        list: A list of relevant information entries retrieved from the knowledge base.
    """
    metadata = config.get("metadata", {})
    owner_id = metadata.get("owner_id")

    vector_store = PGVector(
        embeddings=OpenAIEmbeddings(model="text-embedding-3-large"),
        connection=os.getenv("POSTGRES_URL", ""),
        use_jsonb=True,
    )

    print(f"Searching for: {raw_input} with owner_id: {owner_id}")

    results = vector_store.similarity_search(
        query=raw_input,
        k=1,
        filter={
            "owner_id": owner_id,
        },
    )

    return results


def get_tools():
    """Retorna a lista de ferramentas disponíveis para o agente."""
    return [
        retrieve_availability_and_prices,
        look_for_information_that_i_don_t_know,
    ]
