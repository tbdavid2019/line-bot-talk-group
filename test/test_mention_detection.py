#!/usr/bin/env python3
"""
測試 Bot mention 檢測邏輯
"""
import re

class MockMentionee:
    def __init__(self, index, length, user_id=None, is_self=False, target_type="user"):
        self.index = index
        self.length = length
        self.user_id = user_id
        self.is_self = is_self
        self.type = target_type

class MockMention:
    def __init__(self, mentionees=None):
        self.mentionees = mentionees or []

class MockMessage:
    def __init__(self, text, mention=None):
        self.text = text
        self.mention = mention

class MockEvent:
    def __init__(self, text, mention=None):
        self.message = MockMessage(text, mention)

def is_bot_mentioned(event, bot_id=None, text=None):
    """
    檢查是否 Bot 被提及
    """
    if text is None:
        if not hasattr(event, 'message') or not hasattr(event.message, 'text'):
            return False
        text = event.message.text
    
    if not text:
        return False
    
    mention = getattr(getattr(event, 'message', None), 'mention', None)
    
    # 1. 檢查 LINE 官方提供的 Mention 物件
    if mention and hasattr(mention, 'mentionees') and mention.mentionees:
        # 遍歷所有 mentionee
        for mentionee in mention.mentionees:
            # 官方支援 is_self 屬性（當被 @ 的對象是當前 Bot 時為 True）
            if getattr(mentionee, 'is_self', False) is True:
                return True
            if isinstance(mentionee, dict) and (mentionee.get('isSelf') is True or mentionee.get('is_self') is True):
                return True
        
        # 若有 mention 物件但所有 mentionee 都不是本 Bot (is_self != True)
        # 代表用戶明確是在 @ 其他人 或 @All，不應誤判為呼叫 Bot
        return False
    
    # 2. 若無 LINE 原生 mention 物件（用戶純文字手動輸入），檢查是否明確 @ Bot ID
    if bot_id:
        # 檢查是否包含 @bot_id 或 ＠bot_id
        bot_id_pattern = rf'(?<![\w])[@＠]{re.escape(bot_id)}(?![\w])'
        if re.search(bot_id_pattern, text, re.IGNORECASE):
            return True
    
    # 3. 純文字手動輸入呼叫通用關鍵詞（例如「@Bot 請問...」、「@機器人 幫我...」）
    # 必須以 @ 或 ＠ 開頭接關鍵詞，避免內文中無意出現的單詞誤觸發
    text_stripped = text.strip()
    generic_patterns = [
        r'^[@＠](bot|機器人|摘要王)\b',
        r'^[@＠](bot|機器人|摘要王)\s+',
        r'^[@＠](bot|機器人|摘要王)[:：,，]'
    ]
    for pattern in generic_patterns:
        if re.search(pattern, text_stripped, re.IGNORECASE):
            return True
    
    return False


def extract_clean_question(text: str, event=None, bot_id: str = None) -> str:
    """
    從被 @ 提及的訊息中提取乾淨的問題文字，移除 @Bot 或 @提及 部分
    """
    if not text:
        return ""
    
    clean_text = text
    mention = getattr(getattr(event, 'message', None), 'mention', None) if event else None
    
    # 1. 若有 LINE 原生 mention，利用 index 與 length 移除對應的 mention 字串
    if mention and hasattr(mention, 'mentionees') and mention.mentionees:
        mentionees = sorted(
            [m for m in mention.mentionees if getattr(m, 'index', None) is not None and getattr(m, 'length', None) is not None],
            key=lambda x: getattr(x, 'index'),
            reverse=True
        )
        for m in mentionees:
            idx = getattr(m, 'index')
            length = getattr(m, 'length')
            if getattr(m, 'is_self', False) is True or (isinstance(m, dict) and m.get('isSelf') is True):
                clean_text = clean_text[:idx] + clean_text[idx+length:]
    
    # 2. 若還有殘留的 @bot_id 或 @Bot / @機器人 / @摘要王 前綴，進行正則移除
    if bot_id:
        clean_text = re.sub(rf'(?<![\w])[@＠]{re.escape(bot_id)}(?![\w])', '', clean_text, flags=re.IGNORECASE)
        
    clean_text = re.sub(r'^[@＠](bot|機器人|摘要王)\s*[:：,，]?\s*', '', clean_text.strip(), flags=re.IGNORECASE)
    
    return clean_text.strip()


def test_is_bot_mentioned():
    """測試 Bot mention 檢測函數"""
    print("🤖 Bot Mention 檢測測試")
    print("=" * 50)
    
    bot_id = "377mwhqu"
    
    # 模擬各種 Mention 情境
    mention_self = MockMention([MockMentionee(0, 8, user_id="U12345", is_self=True)])
    mention_other_alice = MockMention([MockMentionee(0, 6, user_id="U67890", is_self=False)])
    mention_all = MockMention([MockMentionee(0, 4, is_self=False, target_type="all")])
    
    test_cases = [
        # 1. LINE 原生 Mention @Bot (is_self=True)
        ("@AI助理 請問天氣如何？", mention_self, True, "LINE 原生 mention Bot (is_self=True)"),
        ("@機器人 幫我摘要", mention_self, True, "LINE 原生 mention 且名稱為機器人"),
        
        # 2. LINE 原生 Mention @其他人 (is_self=False) - 過去會誤判的情境！
        ("@Alice 你好嗎？", mention_other_alice, False, "LINE 原生 mention 其他人 (Alice)"),
        ("@Alice 這個 bot 怎麼用？", mention_other_alice, False, "LINE 原生 mention 其他人但內文含有 bot (不應觸發)"),
        ("@Alice 機器人好像壞了", mention_other_alice, False, "LINE 原生 mention 其他人但內文含有機器人 (不應觸發)"),
        ("@Alice @.. 哈哈", mention_other_alice, False, "LINE 原生 mention 其他人且含有 @.. (不應觸發)"),
        ("@All 請大家注意！", mention_all, False, "LINE 原生 mention @All (不應觸發)"),
        ("@All 群組 bot 已上線", mention_all, False, "LINE 原生 mention @All 且內文有 bot (不應觸發)"),
        
        # 3. 手動輸入 Bot 官方 ID (無 LINE mention 物件)
        ("@377mwhqu 你好", None, True, "手打官方 ID 提及 (@377mwhqu)"),
        ("＠377mwhqu 什麼是 AI？", None, True, "手打全形符號官方 ID (＠377mwhqu)"),
        ("@377mwhqu! 測試", None, True, "手打官方 ID 後接標點符號"),
        
        # 4. 手動輸入通用 Bot 前綴呼叫 (無 LINE mention 物件)
        ("@Bot 請問天氣如何？", None, True, "手動以 @Bot 開頭呼叫"),
        ("@bot: 什麼是機器學習", None, True, "手動以 @bot: 開頭呼叫"),
        ("@機器人 請幫我解釋 AI", None, True, "手動以 @機器人 開頭呼叫"),
        ("@摘要王 總結一下", None, True, "手動以 @摘要王 開頭呼叫"),
        
        # 5. 一般文字中的誤判排除情境 (重要！)
        ("@.. 今天心情不好", None, False, "手打 @.. (不應觸發)"),
        ("@  測試空白", None, False, "手打 @ 加空格 (不應觸發)"),
        ("@john 你好嗎？", None, False, "手打 @其他人 (無 mention 也非 bot)"),
        ("今天天氣不錯", None, False, "一般訊息無提及"),
        ("我喜歡這個 bot", None, False, "一般訊息內文包含 bot 但無 @ 開頭"),
        ("這台機器人很聰明", None, False, "一般訊息內文包含機器人但無 @ 開頭"),
        ("我的 email 是 service@377mwhqu.com", None, False, "Email 地址包含 bot ID"),
        ("價錢 @ 100元", None, False, "單純 @ 符號用於價格/地點"),
    ]
    
    passed = 0
    failed = 0
    for text, mention, expected, description in test_cases:
        event = MockEvent(text, mention)
        result = is_bot_mentioned(event, bot_id)
        
        if result == expected:
            status = "✅"
            passed += 1
        else:
            status = "❌"
            failed += 1
        print(f"{status} {description}")
        print(f"   輸入: '{text}' (Mention: {type(mention).__name__ if mention else 'None'})")
        print(f"   預期: {expected}, 實際: {result}")
        print()
    
    print("=" * 50)
    print(f"測試結果：通過 {passed}/{len(test_cases)} 個，失敗 {failed} 個")
    print("=" * 50)
    assert failed == 0, f"有 {failed} 個測試案例失敗！"


def test_extract_clean_question():
    """測試問題提取與清理"""
    print("\n🧹 問題清理測試 (extract_clean_question)")
    print("=" * 50)
    
    bot_id = "377mwhqu"
    mention_self = MockMention([MockMentionee(0, 6, user_id="U12345", is_self=True)])
    
    test_cases = [
        ("@AI助理 什麼是 Python 的 @decorator？", mention_self, "什麼是 Python 的 @decorator？", "保留問題內部的 @ 符號"),
        ("@377mwhqu 什麼是機器學習？", None, "什麼是機器學習？", "手打 @bot_id 清理"),
        ("@Bot: 請解釋什麼是神經網絡", None, "請解釋什麼是神經網絡", "手打 @Bot: 前綴清理"),
        ("@機器人 幫我寫一首詩", None, "幫我寫一首詩", "手打 @機器人 前綴清理"),
    ]
    
    for text, mention, expected, description in test_cases:
        event = MockEvent(text, mention)
        result = extract_clean_question(text, event, bot_id)
        status = "✅" if result == expected else "❌"
        print(f"{status} {description}")
        print(f"   原始: '{text}'")
        print(f"   清理後: '{result}' (預期: '{expected}')")
        assert result == expected, f"清理結果不符合預期: {result} != {expected}"
        print()


if __name__ == "__main__":
    test_is_bot_mentioned()
    test_extract_clean_question()
    print("🎉 所有測試全部通過！")

