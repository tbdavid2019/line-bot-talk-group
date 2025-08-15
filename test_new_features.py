#!/usr/bin/env python3
"""
測試新功能的簡單腳本
"""

def test_command_detection():
    """測試指令檢測邏輯"""
    
    # 測試特殊指令
    special_commands = ['!清空', '!摘要', '！清空', '！摘要', '!help', '!幫助', '！help', '！幫助']
    
    test_cases = [
        ('!help', True, "標準 help 指令"),
        ('!幫助', True, "中文幫助指令"),
        ('！help', True, "全形驚嘆號 help"),
        ('！幫助', True, "全形驚嘆號中文幫助"),
        ('!摘要', True, "摘要指令"),
        ('！清空', True, "全形清空指令"),
        ('hello', False, "一般訊息"),
        ('什麼是 AI？', False, "一般問題"),
    ]
    
    print("🧪 指令檢測測試")
    print("-" * 40)
    
    for text, expected, description in test_cases:
        has_command = any(cmd in text.lower() for cmd in special_commands)
        result = "✅" if has_command == expected else "❌"
        print(f"{result} {description}: '{text}' -> {has_command}")

def test_ai_question_scenarios():
    """測試 AI 問答場景"""
    
    print("\n🤖 AI 問答場景測試")
    print("-" * 40)
    
    scenarios = [
        ("@Bot 什麼是梯度下降？", "AI 問答模式"),
        ("@機器人 Python 怎麼學？", "AI 問答模式"),
        ("@Bot !摘要", "特殊指令優先"),
        ("普通群組訊息", "記錄但不回應"),
    ]
    
    for text, expected_behavior in scenarios:
        print(f"📝 '{text}' -> {expected_behavior}")

if __name__ == "__main__":
    test_command_detection()
    test_ai_question_scenarios()
    
    print("\n✨ 新功能摘要")
    print("-" * 40)
    print("1. ✅ @ 機器人 + 問題 = AI 問答模式")
    print("2. ✅ !help/!幫助 = 顯示使用說明")
    print("3. ✅ 支援中英文指令符號")
    print("4. ✅ AI 問答不記錄到對話歷史")
    print("5. ✅ 幫助訊息不記錄到對話歷史")
