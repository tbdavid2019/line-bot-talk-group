#!/usr/bin/env python3
"""
簡單的 Gemini 圖片生成測試腳本
用於直接測試圖片生成功能，不通過 LINE Bot
"""
import os
import base64
import mimetypes
from datetime import datetime

# 載入環境變數
if os.getenv('API_ENV') != 'production':
    from dotenv import load_dotenv
    load_dotenv()

def test_simple_image_generation():
    """簡單測試圖片生成"""
    
    try:
        from google import genai as genai_v2
        from google.genai import types
        
        # 取得 API Key
        api_key = os.getenv('GEMINI_IMAGE_API_KEY') or os.getenv('GEMINI_API_KEY')
        if not api_key:
            print("❌ 未設定 API Key")
            return False
            
        print(f"🔑 使用 API Key: {api_key[:10]}...{api_key[-5:]}")
        
        # 建立 client
        client = genai_v2.Client(api_key=api_key)
        model = "gemini-2.5-flash-image-preview"
        
        # 測試提示詞
        test_prompts = [
            "Create a photorealistic image of a giraffe. Do not provide text description, only generate the actual image.",
            "Generate a detailed visual artwork showing a red apple on a wooden table. Output image only, no text.",
            "Draw: cute cat sitting in sunlight. Visual output required."
        ]
        
        for i, prompt in enumerate(test_prompts, 1):
            print(f"\n🎨 測試 {i}: {prompt[:50]}...")
            
            contents = [
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(text=prompt),
                    ],
                ),
            ]
            
            generate_content_config = types.GenerateContentConfig(
                response_modalities=["IMAGE", "TEXT"],
            )
            
            chunk_count = 0
            has_image = False
            text_response = ""
            
            try:
                for chunk in client.models.generate_content_stream(
                    model=model,
                    contents=contents,
                    config=generate_content_config,
                ):
                    chunk_count += 1
                    print(f"  📦 處理 chunk {chunk_count}")
                    
                    if (
                        chunk.candidates is None
                        or chunk.candidates[0].content is None
                        or chunk.candidates[0].content.parts is None
                    ):
                        print(f"    ⚠️ Chunk {chunk_count} 無有效內容")
                        continue
                        
                    part = chunk.candidates[0].content.parts[0]
                    print(f"    🔍 Part 類型: {type(part)}")
                    
                    # 檢查圖片數據
                    if hasattr(part, 'inline_data') and part.inline_data:
                        if hasattr(part.inline_data, 'data') and part.inline_data.data:
                            print(f"    ✅ 找到圖片數據！大小: {len(part.inline_data.data)} bytes")
                            print(f"    📊 MIME 類型: {part.inline_data.mime_type}")
                            has_image = True
                            
                            # 儲存圖片到本地檔案
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            extension = mimetypes.guess_extension(part.inline_data.mime_type) or '.png'
                            filename = f"test_image_{i}_{timestamp}{extension}"
                            
                            with open(filename, 'wb') as f:
                                f.write(part.inline_data.data)
                            print(f"    💾 圖片已儲存到: {filename}")
                        else:
                            print(f"    ⚠️ inline_data 存在但無數據")
                    else:
                        print(f"    ℹ️ 無 inline_data")
                    
                    # 檢查文字
                    if hasattr(part, 'text') and part.text:
                        text_response += part.text
                        print(f"    📝 文字內容: {part.text[:50]}...")
                    elif hasattr(chunk, 'text') and chunk.text:
                        text_response += chunk.text
                        print(f"    📝 Chunk 文字: {chunk.text[:50]}...")
                
                print(f"  📊 總共處理 {chunk_count} chunks")
                print(f"  🖼️ 有圖片: {'是' if has_image else '否'}")
                print(f"  📝 文字回應: {text_response[:100]}..." if text_response else "  📝 無文字回應")
                
                if has_image:
                    print(f"  🎉 測試 {i} 成功！")
                    return True
                else:
                    print(f"  ❌ 測試 {i} 失敗：只有文字，無圖片")
                    
            except Exception as e:
                print(f"  ❌ 測試 {i} 錯誤: {e}")
                
        print("\n❌ 所有測試都失敗")
        return False
        
    except ImportError as e:
        print(f"❌ 匯入錯誤: {e}")
        return False
    except Exception as e:
        print(f"❌ 測試錯誤: {e}")
        return False

if __name__ == "__main__":
    print("🧪 開始 Gemini 圖片生成測試...")
    success = test_simple_image_generation()
    
    if success:
        print("\n🎉 測試成功！圖片生成功能正常。")
    else:
        print("\n❌ 測試失敗！請檢查 API 設定或模型可用性。")
        print("\n💡 建議：")
        print("1. 檢查 API Key 是否有圖片生成權限")
        print("2. 檢查帳戶配額是否足夠")
        print("3. 嘗試更具體的英文描述")
        print("4. 等待一段時間後再試（可能是暫時限制）")
