"""Gate 2: after watching it, does anyone ask how to make it?

Measured on 240 TikTok comments: 19% want on `ai photo shoot`, 4% on `ai skit`. The line that
matters is the one the upstream radar never draws — a person who wants to make the thing is a
user; a person saying "AI is crazy" is an audience.

Kept deliberately narrow: thanks and praise are not want, and "is this AI?" is curiosity.
"""
from __future__ import annotations

from . import llm

SYSTEM = (
    "Label each comment under a video: is the person asking to be shown how to make the same thing?\n"
    "React, whatever the wording, when the comment is not that:\n"
    "- 'what is this', 'what is lupa', 'what is ai', 'what did I just watch': asking what the thing "
    "IS, not how to make it.\n"
    "- 'I did mine with Gemini', 'I have the prompt', 'I copied it and it failed': they already "
    "tried, and saying how you made it is not asking to be shown, even when an app or model is named.\n"
    "- praise, thanks, laughter, insults, a rant, 'is this AI?', a question about the song or the creator.\n"
    "- ordering from you: 'part 2?', 'post more', 'do X next', 'please make one about Y', 'make me "
    "one', 'do a signature for my name Z', 'make one with my photo'. They want to watch, or they "
    "want your output done for them. Neither is them making it.\n"
    "Want only when the comment asks for a recipe or a tool to reproduce it: how, where, which "
    "app/model/prompt/preset/font, 'tutorial?', 'teach me', 'I need this', 'mine "
    "won't work, help', tagging a friend to do it. A failure with no question ('it says it's against "
    "the guidelines') is a report; only 'what do i do' / 'can someone help' makes it want.\n"
    "Sell when it advertises: 'link in bio', 'dm me', referral code, their own product.\n"
    "Past tense in the first person with no question ('I did mine with X', 'I used Y', 'mine came "
    "out fine') is always a report, never want.\n"
    "If the comment asks you to produce the thing itself, for a named person, pet or photo, it is "
    "an order however politely it is phrased: 'do a signature for my name Ali' is react, 'how do i "
    "make a signature' is want.\n"
    "Examples, input -> label: 'how do you make this' -> want; 'tutorial please' -> want; 'do one for my "
    "name Ali' -> react; 'part 2?' -> react; 'this is insane' -> react.\n"
    "Answer with JSON only, one row per input. The label is exactly one of three words: "
    "\"want\", \"react\" or \"sell\" — never a sentence. [{\"i\": 0, \"label\": \"want\"}]"
)

WANT = 0.20
BATCH = 12  # one 24-comment call scored 23/24; at 12 it was 24/24


def share(texts: list[str], model: str) -> tuple[int, int, list[str], int]:
    """(wanted, total, first few wanted comments, calls made)."""
    texts = [t for t in texts if t][:120]
    if not texts:
        return 0, 0, [], 0
    got, calls = llm.ask(model, SYSTEM, [{"comment": t[:200]} for t in texts], "label",
                         size=BATCH)
    wanted = [texts[i] for i, v in got.items() if v == "want"]
    return len(wanted), len(got), [t[:90] for t in wanted[:3]], calls
