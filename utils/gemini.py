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
    "tarot", "fool", "klein", "seer", "clown", "magician",
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
        "others. Choose one and swear fealty at Sequence 9 with `/pathway choose <name>`."
    ),
    "corruption": (
        "Corruption accumulates from rule infractions, failed rituals, and prolonged "
        "slumber. When it grows too high (≥80%), you suffer a Mental Breakdown: "
        "your words twist into ravings, and the Fog of History may "
        "banish you until you are cleansed."
    ),
    "loss of control": (
        "Loss of control is the doom of every careless Beyonder — the moment the "
        "Beyonder characteristic overcomes the self. In this server it manifests as "
        "gibberish speech, Zalgo-distorted names, and temporary banishment to the Fog."
    ),
    "voice": (
        "Voice channels (VC) are the dominant engine of potion digestion! Being active "
        "in VC awards continuous digestion ticks every 60 seconds (Sequence 9 requires 72 hours "
        "of continuous VC). Remaining unmuted in a channel with other members grants an additional +25% bonus."
    ),
    "mortal": (
        "Members join as ordinary mortals without powers or Beyonder commands. "
        "Only members who wish to acquire supernatural authority, advance through the sequences, "
        "and potentially rise to high ranks (Demigods, Angels, or Server Admins) brew and drink their "
        "Sequence 9 potion using `/pathway choose <pathway>`. Mortals cannot use Beyonder abilities."
    ),
    "brew": (
        "To brew and drink your initial potion and awaken as a Beyonder, run `/pathway choose <pathway_name>`. "
        "To brew higher sequence potions, you must acquire the target sequence formula, ingredients, and "
        "characteristic from the shop or bounties, reach 100% digestion, and run `/advance`."
    ),
    "power": (
        "Ascending through the sequences grants elevated prestige, hoisted Discord roles (Sequence 4–0), "
        "access to Archangel adjudication, and true godhood at Sequence 0. Mortals hold no powers until they "
        "choose to brew and drink their potion."
    ),
    "backlash": (
        "Advancement rituals carry risk (5% at Seq 8 up to 40% at Seq 1). High sanity reduces backlash risk, "
        "while corruption increases it. On backlash failure, ingredients, gold, and formulas are consumed, "
        "and you suffer severe digestion, sanity, and corruption penalties."
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
            "acting method, or the corruption that gnaws at Beyonders, and the "
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
