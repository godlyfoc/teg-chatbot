"""Fallback messages for the RAG pipeline."""

from app.services.language import LanguageCode


def fallback_message(user_language: LanguageCode) -> str:
    """Safe fallback when retrieval or validation cannot produce a grounded answer."""
    if user_language == "ga":
        return (
            "Níl an t-eolas a iarradh ar fáil ar láithreán gréasáin TEG faoi láthair. "
            "Ní féidir liom freagra a thabhairt bunaithe ar ábhar teg.ie don cheist seo.\n\n"
            "**Cad is féidir leat a dhéanamh:**\n"
            "- Cuairt a thabhairt ar [teg.ie](https://www.teg.ie) chun na hailt ábhartha a lorg\n"
            "- Teagmháil a dhéanamh le TEG ag **teg@mu.ie** le haghaidh tuilleadh cabhrach"
        )
    return (
        "The information you requested is not available on the TEG website at this time. "
        "I cannot answer this question based on teg.ie content.\n\n"
        "**What you can do:**\n"
        "- Visit [teg.ie](https://www.teg.ie) to browse relevant sections\n"
        "- Contact TEG at **teg@mu.ie** for further assistance"
    )


def insufficient_context_message(user_language: LanguageCode) -> str:
    """When reranked context exists but cannot answer the specific question."""
    if user_language == "ga":
        return (
            "Níl go leor eolais sna leathanaigh a aimsíodh ar teg.ie chun freagra iomlán a thabhairt ar do cheist. "
            "Ní féidir liom tuilleadh sonraí a chur leis.\n\n"
            "Molaim duit cuairt a thabhairt ar [teg.ie](https://www.teg.ie) nó teagmháil a dhéanamh le TEG ag **teg@mu.ie**."
        )
    return (
        "The teg.ie pages retrieved do not contain enough information to fully answer your question. "
        "I cannot add details beyond what is available in the source content.\n\n"
        "Please visit [teg.ie](https://www.teg.ie) or contact TEG at **teg@mu.ie** for further assistance."
    )
