"""Prompts for grounded RAG response generation."""

from app.models.retrieval import RetrievedChunk
from app.services.language import LanguageCode, bilingual_system_prompt
from app.services.retrieval.context import format_retrieval_context

RESPONSE_FORMAT_EN = """
Format your reply exactly as follows:

## Answer
Write a concise, well-structured answer for a general audience using **markdown**:
- Open with a short summary paragraph (1–2 sentences).
- Use **bold** for key terms, exam levels, and important dates.
- Use bullet points (`-`) or numbered lists (`1.`) when listing multiple items.
- Use `###` subheadings only when the answer has clearly separate sections.
- Keep paragraphs short (2–4 sentences max) and easy to scan.
- Use only facts from the provided excerpts.
- **Write the Answer in English**, even when source excerpts are in Irish — translate the facts into English.
- **Cite sources inline** using the excerpt numbers from the context, e.g. `TEG offers exams at multiple levels [1].` or `Registration opens in spring [2].`
- Place citation markers `[1]`, `[2]`, etc. immediately after the sentence or clause they support.

## Sources
List every source you cited, using the **same numbers** as the excerpt labels in the context:
1. [Page Title](https://full-url)
2. [Another Page](https://full-url)

Rules:
- Use ONLY the provided teg.ie excerpts. Do not use outside knowledge.
- If the excerpts do not contain enough information, state that clearly in the Answer section and still list any partially relevant sources.
- Every factual claim must include an inline citation marker and appear in Sources.
- Citation numbers must match the `[1]`, `[2]` excerpt labels from the context block.
- Respond in English only.
- Output valid markdown only — no HTML tags.
""".strip()

RESPONSE_FORMAT_GA = """
Formáidigh do fhreagra mar seo a leanas:

## Answer
Scríobh freagra gonta, dea-struchtúrtha don phobal i gcoitinne ag úsáid **markdown**:
- Tosaigh le achoimre ghearr (1–2 abairt).
- Úsáid **téacs trom** do théarmaí tábhachtacha, leibhéil scrúdaithe, agus dátaí.
- Úsáid liostaí bullet (`-`) nó liostaí uimhrithe (`1.`) nuair a bhíonn míreanna iolracha le liostú.
- Úsáid `###` focheannteáin ach nuair a bhíonn codanna ar leith sa fhreagra.
- Coinnigh paragrafanna gearra (2–4 abairt ar a mhéad) agus éasca le léamh.
- Úsáid fíricí ó na habhairtí amháin.
- **Scríobh an Answer i nGaeilge**, fiú nuair a bhíonn na habhairtí i mBéarla — aistrigh na fíricí go Gaeilge.
- **Luaigh foinsí sa téacs** le huimhreacha na n-abairtí ón gcomhthéacs, m.sh. `Cuireann TEG scrúduithe ar fáil [1].`
- Cuir marcóirí tagartha `[1]`, `[2]` go díreach i ndiaidh na habairte a thacaíonn leo.

## Sources
Liostaigh gach foinse a luaigh tú, ag úsáid **na huimhreacha céanna** le lipéid na n-abairtí sa chomhthéacs:
1. [Teideal an Leathanaigh](https://full-url)
2. [Leathanach Eile](https://full-url)

Rialacha:
- Úsáid NA habhairtí teg.ie a cuireadh ar fáil. Ná húsáid eolas seachtrach.
- Mura bhfuil go leor eolais sna habhairtí, abair é go soiléir sa chuid Answer agus liostaigh fós aon fhoinsí ábhartha.
- Caithfidh gach fíric marcóir tagartha inlíne agus iontráil sa liosta Sources.
- Caithfidh uimhreacha tagartha meaitseáil le lipéid `[1]`, `[2]` sa chomhthéacs.
- Freagair i nGaeilge amháin.
- Aschuir markdown bhailí amháin — gan chlibeanna HTML.
""".strip()


def build_rag_system_message(
    *,
    context_chunks: list[RetrievedChunk],
    max_context_chars: int,
    query_language: LanguageCode,
) -> str:
    base = bilingual_system_prompt(query_language)
    context = format_retrieval_context(context_chunks, max_chars=max_context_chars)
    response_format = RESPONSE_FORMAT_GA if query_language == "ga" else RESPONSE_FORMAT_EN
    return f"{base}\n\n{response_format}\n\n---\n{context}\n---"


def build_regeneration_message(validation_errors: list[str], query_language: LanguageCode) -> str:
    issues = "\n".join(f"- {error}" for error in validation_errors)
    if query_language == "ga":
        return (
            "Theip ar bhailíochtú ar an bhfreagra roimhe seo. Seo na fadhbanna:\n"
            f"{issues}\n\n"
            "Déan iarracht eile. Úsáid ach na habhairtí a cuireadh ar fáil. "
            "Cinntigh go bhfuil gach fíric bunaithe ar na foinsí agus go bhfuil naisc chearta sa chuid Sources."
        )
    return (
        "Your previous response failed validation. Issues found:\n"
        f"{issues}\n\n"
        "Try again. Use only the provided excerpts. "
        "Ensure every fact is grounded, include inline citation markers like [1] in the Answer, "
        "and Sources contains numbered markdown links matching those markers."
    )
