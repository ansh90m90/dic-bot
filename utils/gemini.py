"""Gemini-backed Spirit World Oracle.

Thin async client over the Gemini REST API (``generateContent``). If no API key
is configured — or the API call fails — the Oracle falls back to a curated,
topic-confined lore bank so the command still behaves correctly.
"""
from __future__ import annotations

import aiohttp

import config
from utils.persona import ORACLE_REFUSAL, ORACLE_SYSTEM_PROMPT

_GENERATE_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

# Curated fallback bank (used only when the LLM is unreachable/unconfigured).
_LOTM_KEYWORDS = (
    "pathway", "sequence", "beyonder", "potion", "digestion", "acting",
    "sealed artifact", "tarot", "fool", "klein", "seer", "clown", "magician",
    "faceless", "marionettist", "bizarro sorcerer", "scholar of yore",
    "miracle invoker", "attendant of mysteries", "error", "door", "visionary",
    "hanged man", "white tower", "sun", "tyrant", "darkness", "death",
    "twilight giant", "red priest", "demoness", "hermit", "paragon",
    "chained", "abyss", "moon", "mother", "black emperor", "justiciar",
    "wheel of fortune", "corruption", "loss of control", "uniqueness",
    "apotheosis", "god", "angel", "demigod", "saint", "madness", "sanity",
    "lotm", "lord of the mysteries", "amnis", "roselle", "gehrman sparrow",
)

_FALLBACK_ANSWERS = {
    "sequence": (
        "There are 22 Pathways, each a ladder of ten Sequences descending from 9 "
        "(the entry) to 0 (godhood). Beyonders advance by consuming potions brewed "
        "from Beyonder characteristics and rare ingredients, then digesting them "
        "through the Acting Method — embodying the role of their current Sequence."
    ),
    "pathway": (
        "The 22 Pathways are grouped under above-sequence beings: the Lord of the "
        "Mysteries (Fool, Error, Door), God Almighty (Visionary, Hanged Man, White "
        "Tower, Sun, Tyrant), Eternal Darkness (Darkness, Death, Twilight Giant), and "
        "others. Choose one and swear fealty at Sequence 9."
    ),
    "corruption": (
        "Corruption accumulates from rule infractions, failed rituals, and the misuse "
        "of Sealed Artifacts. When it grows too high, you suffer a Mental Breakdown: "
        "your perks fail, your name twists into ravings, and the Fog of History may "
        "banish you until you are cleansed."
    ),
    "loss of control": (
        "Loss of control is the doom of every careless Beyonder — the moment the "
        "Beyonder characteristic overcomes the self. In this server it manifests as "
        "gibberish speech, Zalgo-distorted names, and temporary banishment to the Fog."
    ),
    "sealed artifact": (
        "Sealed Artifacts are equipable items of terrible power and terrible price. A "
        "Grade 1 artifact may double your digestion, yet devour one in ten of your "
        "messages and drip corruption into you each day. Seal them before you rest."
    ),
}


def _fallback_answer(question: str) -> str:
    lowered = question.lower()
    for keyword, answer in _FALLBACK_ANSWERS.items():
        if keyword in lowered:
            return answer
    if any(k in lowered for k in _LOTM_KEYWORDS):
        return (
            "The gray fog parts but a little. Ask of a specific pathway, sequence, "
            "Sealed Artifact, or the corruption that gnaws at Beyonders, and the "
            "Spirit World shall answer more precisely."
        )
    return ORACLE_REFUSAL


async def ask_oracle(question: str, spoiler: bool = False) -> str:
    """Ask the Spirit World Oracle a question. Returns the Oracle's answer text."""
    if not config.GEMINI_API_KEY:
        return _fallback_answer(question)

    system = ORACLE_SYSTEM_PROMPT
    if spoiler:
        system += (
            "\n\nSPOILER PROTOCOL: The questioner has explicitly tagged `spoiler:true`. "
            "Full novel spoilers are now permitted."
        )
    else:
        system += (
            "\n\nSPOILER PROTOCOL: Do NOT reveal major novel spoilers. If a complete "
            "answer requires them, give a spoiler-free summary and note that spoilers "
            "remain hidden behind the gray fog."
        )

    payload = {
        "system_instruction": {"parts": [{"text": system}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "generationConfig": {
            "temperature": config.GEMINI_TEMPERATURE,
            "maxOutputTokens": 800,
        },
    }
    url = _GENERATE_URL.format(model=config.GEMINI_MODEL)

    try:
        timeout = aiohttp.ClientTimeout(total=30)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url, params={"key": config.GEMINI_API_KEY}, json=payload
            ) as resp:
                if resp.status != 200:
                    return _fallback_answer(question)
                data = await resp.json()
    except (aiohttp.ClientError, ValueError, KeyError):
        return _fallback_answer(question)

    try:
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError, TypeError):
        return _fallback_answer(question)
    return text or _fallback_answer(question)
