import anthropic
import asyncio
import base64
import os

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


async def get_ai_guess(drawing_base64: str, category: str) -> str:
    """
    Rasm (base64 PNG) va kategoriya asosida Claude dan taxmin oladi.
    Sync Anthropic SDK ni thread pool da ishlatamiz.
    """
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _sync_guess, drawing_base64, category)
    return result


def _sync_guess(drawing_base64: str, category: str) -> str:
    # Base64 dan data: prefix ni tozalaymiz
    if "," in drawing_base64:
        drawing_base64 = drawing_base64.split(",")[1]

    if not drawing_base64:
        return "bilmadim"

    try:
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=50,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": drawing_base64,
                            },
                        },
                        {
                            "type": "text",
                            "text": (
                                f"Bu o'yin uchun chizilgan abstrakt rasm. "
                                f"Kategoriya: {category}. "
                                f"Bu rasm nima ekanligini taxmin qil. "
                                f"FAQAT bitta so'z yoz, hech narsa qo'shma."
                            ),
                        },
                    ],
                }
            ],
        )
        guess = message.content[0].text.strip()
        # Faqat birinchi so'zni olamiz
        return guess.split()[0] if guess else "bilmadim"

    except Exception as e:
        print(f"AI xatosi: {e}")
        return "bilmadim"