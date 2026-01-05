from linebot.v3.messaging import (
    FlexMessage,
    FlexContainer
)

def create_flex_message(text: str, title: str = "AI 回應", author: str = "Gemini", header_text: str = "AI 助理") -> FlexMessage:
    """
    Create a Flex Message with the specified style.
    """
    
    # Construct the Flex Message JSON structure
    flex_json = {
        "type": "bubble",
        "header": {
            "type": "box",
            "layout": "horizontal",
            "contents": [
                {
                    "type": "text",
                    "text": "🤖",  # Icon
                    "flex": 0,
                    "margin": "sm"
                },
                {
                    "type": "text",
                    "text": header_text,
                    "weight": "bold",
                    "size": "lg",
                    "color": "#FFFFFF",
                    "flex": 1,
                    "margin": "md"
                }
            ],
            "backgroundColor": "#F4B400",
            "paddingAll": "15px"
        },
        "body": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": title,
                    "weight": "bold",
                    "size": "xl",
                    "color": "#E67E22",
                    "wrap": True
                },
                {
                    "type": "text",
                    "text": f"Model: {author}",
                    "size": "xs",
                    "color": "#7F8C8D",
                    "margin": "xs"
                },
                {
                    "type": "separator",
                    "margin": "md"
                },
                {
                    "type": "text",
                    "text": text,
                    "wrap": True,
                    "size": "md",
                    "margin": "md",
                    "color": "#333333",
                    "lineSpacing": "4px"
                }
            ],
            "paddingAll": "20px"
        },
        "footer": {
            "type": "box",
            "layout": "vertical",
            "contents": [
                {
                    "type": "text",
                    "text": "✨ Powered by AI",
                    "size": "xs",
                    "color": "#AAAAAA",
                    "align": "center"
                }
            ],
            "paddingAll": "10px"
        }
    }

    return FlexMessage(
        alt_text=text[:400] if len(text) > 400 else text,
        contents=FlexContainer.from_dict(flex_json)
    )
