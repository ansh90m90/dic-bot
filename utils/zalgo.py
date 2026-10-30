"""Zalgo text generation for corruption-induced nickname/message distortion."""
from __future__ import annotations

import random

_UPPER = [
    "\u030d", "\u030e", "\u0304", "\u0305", "\u033f", "\u0311", "\u0306",
    "\u0310", "\u0352", "\u0357", "\u0351", "\u0307", "\u0308", "\u030a",
    "\u0342", "\u0313", "\u0314", "\u0309", "\u0363", "\u0364", "\u0365",
    "\u0332", "\u0333", "\u0334", "\u0335", "\u0336",
]
_MID = ["\u0315", "\u031b", "\u0340", "\u0341", "\u0358", "\u0321", "\u0322",
        "\u0327", "\u0328", "\u0334", "\u0335", "\u0336", "\u034f", "\u035c",
        "\u035d", "\u035e", "\u035f", "\u0360", "\u0362", "\u0338", "\u0337"]
_LOWER = ["\u0316", "\u0317", "\u0318", "\u0319", "\u031c", "\u031d", "\u031e",
          "\u031f", "\u0320", "\u0324", "\u0325", "\u0326", "\u0329", "\u032a",
          "\u032b", "\u032c", "\u032d", "\u032e", "\u032f", "\u0330", "\u0331",
          "\u0332", "\u0333", "\u0339", "\u033a", "\u033b", "\u033c", "\u0345",
          "\u0347", "\u0348", "\u0349", "\u034d", "\u034e", "\u0353", "\u0354",
          "\u0355", "\u0356", "\u0359", "\u035a", "\u0323"]


def zalgo(text: str, intensity: int = 3) -> str:
    """Corrupt ``text`` with combining diacritics. Higher intensity = worse."""
    out: list[str] = []
    for ch in text:
        if ch.isspace():
            out.append(ch)
            continue
        out.append(ch)
        for _ in range(random.randint(0, intensity)):
            if random.random() < 0.5:
                out.append(random.choice(_UPPER))
            if random.random() < 0.3:
                out.append(random.choice(_MID))
            if random.random() < 0.3:
                out.append(random.choice(_LOWER))
    return "".join(out)


def gibberish(text: str) -> str:
    """Turn a message into esoteric ravings (used for corrupted users)."""
    words = text.split()
    if not words:
        return text
    ravings = [
        "THE FOG WHISPERS", "I̷ s̷e̷e̷", "the ravings echo", "gibberish",
        "all shall be consumed", "the gray mists", "madness beckons",
        "the True Creator sees", "unravel", "lost to the Spirit World",
    ]
    parts: list[str] = []
    for i, _ in enumerate(words):
        if i % 2 == 0:
            parts.append(zalgo(random.choice(ravings), intensity=2))
        else:
            parts.append(zalgo(words[i], intensity=4))
    return " ".join(parts)
