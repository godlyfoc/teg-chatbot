"""Shared LLM prompts."""

from app.services.language import bilingual_system_prompt, detect_user_language


def build_system_message(user_message: str) -> str:
    user_lang = detect_user_language(user_message)
    return bilingual_system_prompt(user_lang)
