"""Shared vision analysis utility for sending images to Claude Vision API."""

import base64

import anthropic
from PIL import Image

from jarvis.retry import retry_api_call


def analyze_image(api_key: str, image_path: str, question: str, model: str = "claude-sonnet-4-5-20250929") -> str:
    """Send an image to Claude Vision API and return text description.

    Args:
        api_key: Anthropic API key.
        image_path: Path to the image file.
        question: What to analyze about the image.
        model: Model to use for vision analysis.

    Returns:
        Text description from the vision model, or error message.
    """
    try:
        img = Image.open(image_path)
        # Resize to max 1280px wide to control token cost
        if img.width > 1280:
            ratio = 1280 / img.width
            img = img.resize((1280, int(img.height * ratio)), Image.LANCZOS)
            resized_path = image_path.replace(".png", "_resized.png")
            img.save(resized_path)
            image_path = resized_path

        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")

        client = anthropic.Anthropic(api_key=api_key)
        response = retry_api_call(
            client.messages.create,
            model=model,
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/png",
                                "data": image_data,
                            },
                        },
                        {"type": "text", "text": question},
                    ],
                }
            ],
        )
        return response.content[0].text
    except Exception as e:
        return f"Vision analysis error: {e}"
