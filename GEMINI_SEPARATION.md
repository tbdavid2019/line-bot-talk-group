# Gemini API 分離設定說明

## 新的分離式設定

為了讓 LLM（文字對話）和圖片生成功能可以使用不同的 API Key 和模型，現在支援分離設定：

### 環境變數設定

```bash
# Gemini LLM 設定（文字對話、摘要等）
GEMINI_LLM_API_KEY=your_gemini_llm_api_key
GEMINI_LLM_MODEL=gemini-1.5-pro

# Gemini Image 設定（圖片生成）
GEMINI_IMAGE_API_KEY=your_gemini_image_api_key
GEMINI_IMAGE_MODEL=gemini-2.5-flash-image-preview
```

### 功能分配

**使用 LLM 設定的功能：**
- 一般文字對話
- `!摘要` 對話摘要
- `@Bot` AI 問答模式

**使用 Image 設定的功能：**
- `!畫圖` 圖片生成
- `!生成圖片` 圖片生成
- `!image` / `!draw` 圖片生成

### 向後相容

如果你沒有設定新的分離變數，系統會自動使用舊的設定：
- 如果沒有 `GEMINI_LLM_API_KEY`，會使用 `GEMINI_API_KEY`
- 如果沒有 `GEMINI_IMAGE_API_KEY`，會使用 `GEMINI_API_KEY`
- 如果沒有 `GEMINI_LLM_MODEL`，會使用 `GEMINI_MODEL`

### 建議設定

1. **相同 API Key，不同模型：**
   ```bash
   GEMINI_LLM_API_KEY=same_api_key
   GEMINI_LLM_MODEL=gemini-1.5-pro
   
   GEMINI_IMAGE_API_KEY=same_api_key
   GEMINI_IMAGE_MODEL=gemini-2.5-flash-image-preview
   ```

2. **不同 API Key：**
   ```bash
   GEMINI_LLM_API_KEY=llm_project_api_key
   GEMINI_LLM_MODEL=gemini-1.5-pro
   
   GEMINI_IMAGE_API_KEY=image_project_api_key
   GEMINI_IMAGE_MODEL=gemini-2.5-flash-image-preview
   ```

### 測試設定

執行測試腳本檢查設定：
```bash
python test_image_generation.py
```

這會分別測試 LLM 和圖片生成 API 的連接狀態。
