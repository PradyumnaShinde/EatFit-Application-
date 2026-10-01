"""Menu photo -> dish names, using a vision LLM (Google Gemini).
Requires GEMINI_API_KEY. The user always confirms the result before it is saved."""
import json

from .config import settings

PROMPT = """This is a photo of an Indian mess/canteen/restaurant menu (it may be handwritten).
List every food item on it. Reply with JSON only, in exactly this shape:
{"meals": {"breakfast": [], "lunch": [], "snacks": [], "dinner": []},
 "items": [{"name": "Roti", "price": 10}]}
Fill "meals" only if the menu is clearly split by meal; otherwise leave the lists empty.
Use null for unknown prices. Do not invent items that are not in the photo."""


class MenuScanError(Exception):
    pass


def scan_menu(image_bytes: bytes, mime_type: str) -> dict:
    if not settings.gemini_api_key:
        raise MenuScanError("Menu scanning is not configured on the server")
    from google import genai
    from google.genai import types

    try:
        client = genai.Client(api_key=settings.gemini_api_key)
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=[types.Part.from_bytes(data=image_bytes, mime_type=mime_type), PROMPT],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return json.loads(response.text)
    except Exception as e:
        raise MenuScanError(f"Could not read the menu: {e}")
