"""AI fallback: asks Claude to write a public reply when no rule matched."""
from config import ANTHROPIC_API_KEY, AI_MODEL

SYSTEM = """You write public replies to Instagram comments for a business account.
{voice}

Rules:
- Reply in the same language as the comment.
- Only state facts given in the post info below. Never invent prices, hours, or details. If the comment needs info you don't have, politely suggest sending a DM.
- If the comment is spam, abusive, a complaint that needs a human, or doesn't need a reply, output exactly: SKIP
- Output only the reply text, nothing else."""


def available() -> bool:
    return bool(ANTHROPIC_API_KEY)


def ai_reply(text: str, username: str, voice: str, context: str = ""):
    """Returns reply text, or None if AI is unavailable or decides to skip."""
    if not available():
        return None
    system = SYSTEM.format(voice=voice)
    if context:
        system += f"\n\nAbout the post being commented on:\n{context}"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
        msg = client.messages.create(
            model=AI_MODEL,
            max_tokens=150,
            system=system,
            messages=[{"role": "user", "content": f"Comment from @{username}: {text}"}],
        )
        out = msg.content[0].text.strip()
        return None if out.upper().startswith("SKIP") else out
    except Exception as e:
        print(f"[ai] error: {e}")
        return None
