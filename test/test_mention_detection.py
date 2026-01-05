#!/usr/bin/env python3
"""
測試 Bot mention 檢測邏輯
"""

class MockMessage:
    def __init__(self, text, mention=None):
        self.text = text
        self.mention = mention

class MockEvent:
    def __init__(self, text, mention=None):
        self.message = MockMessage(text, mention)

def test_is_bot_mentioned():
    """測試 Bot mention 檢測函數"""
    
    print("🤖 Bot Mention 檢測測試")
    print("=" * 50)
    
    # 導入檢測函數（模擬版本）
    def is_bot_mentioned_test(event, bot_id=None):
        text = event.message.text
        mention = getattr(event.message, 'mention', None)
        
        # 方法2: 檢查文字中是否包含 Bot 的官方 ID
        if bot_id:
            bot_patterns = [
                f'@{bot_id}',
                f'＠{bot_id}',
                f'@{bot_id.lower()}',
                f'＠{bot_id.lower()}'
            ]
            
            for pattern in bot_patterns:
                if pattern in text:
                    return True
        
        # 方法3: 檢查是否有 mention 且文字包含關鍵詞
        if mention:
            bot_keywords = ['bot', 'Bot', 'BOT', '機器人', '摘要王']
            if any(keyword in text for keyword in bot_keywords):
                return True
        
        return False
    
    test_cases = [
        # 應該觸發 Bot 的情況
        ("@377mwhqu 你好", None, True, "官方 ID 提及"),
        ("＠377mwhqu 什麼是 AI？", None, True, "全形符號官方 ID"),
        ("@Bot 請問天氣如何？", "mock_mention", True, "Bot 關鍵詞 + mention"),
        ("@機器人 幫我摘要", "mock_mention", True, "中文關鍵詞 + mention"),
        
        # 不應該觸發 Bot 的情況
        ("@john 你好嗎？", "mock_mention", False, "提及其他人"),
        ("@alice 今天要開會", "mock_mention", False, "提及其他人2"),
        ("今天天氣不錯", None, False, "一般訊息無提及"),
        ("@unknownuser 測試", "mock_mention", False, "提及未知用戶"),
        ("我喜歡這個 bot", None, False, "包含 bot 但無 mention"),
        
        # 邊界情況
        ("@377MWHQU 大寫測試", None, False, "大寫 ID（應該不匹配）"),
        ("email@377mwhqu.com", None, False, "包含 ID 但在 email 中"),
        ("@377mwhqu!", None, True, "ID 後有標點符號"),
    ]
    
    bot_id = "377mwhqu"
    
    for text, mention, expected, description in test_cases:
        event = MockEvent(text, mention)
        result = is_bot_mentioned_test(event, bot_id)
        
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}")
        print(f"   輸入: '{text}'")
        print(f"   預期: {expected}, 實際: {result}")
        print()

def test_special_commands():
    """測試特殊指令優先權"""
    print("🔧 特殊指令優先權測試")
    print("=" * 50)
    
    special_commands = ['!清空', '!摘要', '！清空', '！摘要', '!help', '!幫助', '！help', '！幫助']
    
    test_cases = [
        ("@377mwhqu !摘要", "Bot 提及 + 特殊指令 → 應該執行特殊指令"),
        ("@Bot !help", "Bot 關鍵詞 + 幫助指令 → 應該顯示幫助"),
        ("!清空 @377mwhqu", "特殊指令 + Bot 提及 → 應該執行特殊指令"),
    ]
    
    for text, description in test_cases:
        has_special_command = any(cmd in text.lower() for cmd in special_commands)
        print(f"📝 {description}")
        print(f"   輸入: '{text}'")
        print(f"   包含特殊指令: {has_special_command}")
        print()

if __name__ == "__main__":
    test_is_bot_mentioned()
    test_special_commands()
    
    print("💡 改進建議")
    print("=" * 50)
    print("1. 如果能獲取 Bot 的真實 user_id，可以更精確檢測")
    print("2. 可以考慮添加更多 Bot 的別名或關鍵詞")
    print("3. 特殊指令始終具有最高優先權")
    print("4. 建議在 .env 中設定 LINE_BOT_ID=377mwhqu")
