#!/usr/bin/env python3
"""
一對一對話功能測試腳本
"""

def test_private_conversation_logic():
    """模擬一對一對話的邏輯測試"""
    
    print("🔍 一對一對話邏輯測試")
    print("=" * 50)
    
    # 模擬不同的私人訊息場景
    test_cases = [
        {
            "text": "你好",
            "source_type": "user",
            "expected": "一般 AI 對話",
            "should_reply": True,
            "is_special_command": False
        },
        {
            "text": "什麼是 Python？",
            "source_type": "user", 
            "expected": "一般 AI 對話",
            "should_reply": True,
            "is_special_command": False
        },
        {
            "text": "!help",
            "source_type": "user",
            "expected": "顯示幫助",
            "should_reply": True,
            "is_special_command": True
        },
        {
            "text": "!摘要",
            "source_type": "user",
            "expected": "產生摘要",
            "should_reply": True,
            "is_special_command": True
        }
    ]
    
    special_commands = ['!清空', '!摘要', '！清空', '！摘要', '!help', '!幫助', '！help', '！幫助']
    
    for i, case in enumerate(test_cases, 1):
        text = case["text"]
        source_type = case["source_type"]
        
        # 模擬邏輯判斷
        should_reply = False
        is_ai_question = False
        
        if source_type == 'group':
            # 群組邏輯（這裡不測試）
            pass
        else:
            # 私人對話：所有訊息都回應
            should_reply = True
            has_special_command = any(cmd in text.lower() for cmd in special_commands)
        
        # 判斷會進入哪個處理分支
        if should_reply:
            if text.lower() in ['!清空', '！清空']:
                branch = "清空指令"
            elif text.lower() in ['!摘要', '！摘要']:
                branch = "摘要指令"
            elif text.lower() in ['!help', '!幫助', '！help', '！幫助']:
                branch = "幫助指令"
            elif is_ai_question:
                branch = "AI 問答模式"
            else:
                branch = "一般對話"
        else:
            branch = "不回應"
        
        result = "✅" if branch == case["expected"] or (branch == "一般對話" and case["expected"] == "一般 AI 對話") else "❌"
        
        print(f"{result} 測試 {i}: '{text}'")
        print(f"   預期: {case['expected']}")
        print(f"   實際: {branch}")
        print(f"   should_reply: {should_reply}")
        print()

def check_gemini_model():
    """檢查 Gemini 模型配置"""
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    print("🔧 環境配置檢查")
    print("=" * 50)
    
    gemini_key = os.getenv('GEMINI_API_KEY')
    gemini_model = os.getenv('GEMINI_MODEL', 'gemini-2.5-flash')
    
    print(f"GEMINI_API_KEY: {'✅ 已設定' if gemini_key else '❌ 未設定'}")
    print(f"GEMINI_MODEL: {gemini_model}")
    print()

def debug_tips():
    """提供除錯建議"""
    print("🐛 除錯建議")
    print("=" * 50)
    print("1. 檢查 LINE Bot 日誌，看看是否有錯誤訊息")
    print("2. 確認私人對話的 webhook 有正確接收")
    print("3. 檢查 Firebase 是否正常儲存訊息")
    print("4. 確認 Gemini API 金鑰是否有效")
    print("5. 檢查是否有網路連線問題")
    print()
    print("🔍 檢查方式：")
    print("- 發送 '!help' 看是否有回應")
    print("- 查看終端的 log 輸出")
    print("- 確認 webhook URL 設定正確")

if __name__ == "__main__":
    test_private_conversation_logic()
    check_gemini_model()
    debug_tips()
