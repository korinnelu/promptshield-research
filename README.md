# PromptShield 系統

**基於 LLM 的紅隊攻擊生成與 Prompt Injection 防禦系統**

PromptShield 是一個自動化的 Prompt Injection 攻防與滲透測試框架，專為檢驗大型語言模型 (LLM) 應用的安全性而設計。本系統採用雙向紅藍對抗架構，利用 Google Gemini 作為紅隊主動生成並進化攻擊，結合 NVIDIA NIM Llama 3.3 作為藍隊進行偵測，並透過真實受害者模型 (Victim LLM) 測量資料洩漏風險，最終自動產出具備高度操作性的防禦修補報告。

---

## 核心創新與優勢

與市面上僅進行單向二元分類的靜態偵測工具不同，PromptShield 具備以下核心差異化優勢：

1. **雙向對抗測試 Two-way Adversarial Testing**：不依賴靜態資料集，而是由紅隊 LLM 主動生成未知攻擊，讓攻擊與防禦相互進化，貼近真實駭客思維。
2. **真實效果測量 Real Impact Measurement**：跳脫語義層面的理論判斷，透過受害者模組真實測試攻擊是否造成「資料洩漏」，提供精確的 Breach Rate 商業風險指標。
3. **自適應自動進化 Adaptive Evolution**：紅隊具備自我學習能力，能根據藍隊的反饋與弱點，自動生成更具隱蔽性的攻擊變體，探索系統安全邊界。
4. **自動化可操作報告 Actionable Auto-Reporting**：測試完成後自動輸出專業安全報告，包含漏洞分析、MITRE ATT&CK 映射，以及可直接套用之系統提示詞 (System Prompt) 修補建議。
5. **前沿世界知識融合 World-Aware Knowledge**：支援 2024-2025 最新 Prompt Injection 攻擊策略（如多層上下文注入、行為條件化），確保防禦系統能應對最新威脅。

---

## 系統核心模組

- **Red Team - Google Gemini**：扮演攻擊方，支援 Zero-shot、Chain-of-Thought (CoT) 與 World-aware 等多種提示詞工程策略。
- **Blue Team - NVIDIA NIM Llama 3.3 70B**：扮演防禦方，負責偵測惡意意圖、評估信心度 (Confidence)、嚴重程度 (Severity) 並將攻擊映射至 MITRE 框架。
- **Victim LLM 模組**：模擬企業真實的 LLM 應用（如銀行客服、人資系統），用以檢驗攻擊是否成功繞過系統提示詞並竊取敏感資料。
- **Evaluator 評估模組**：實施標準機器學習評估框架，計算 Precision、Recall、F1-score 及混淆矩陣。
- **Reporter 報告生模組**：彙整測試數據，生成標準化安全評估與緩解建議。

---

## 測試儀表板與工作流

啟動系統後，使用者可透過四個主要介面 (Tabs) 進行不同層次的安全測試：

- **Tab 1: Red vs Blue 紅藍對抗測試**
  快速測試自定義系統描述在隨機生成的五次攻擊下的防禦表現，並輸出信心度與攻擊類型分佈。
- **Tab 2: Benchmark 基準評估**
  執行預設之 15 筆混合資料集（涵蓋正常輸入、明顯攻擊與隱蔽型社交工程），輸出標準化機器學習評估指標 (F1-score)。
- **Tab 3: Adaptive Attack 自適應進化攻防**
  設定進化輪次與觸發閾值，觀察紅隊如何根據藍隊的防禦反饋，逐步演化攻擊敘述以突破防禦系統。
- **Tab 4: Live Target & Report 實時目標測試與報告**
  針對真實業務情境執行最前沿的攻擊測試，測量資料洩漏率 (Breach Rate)，並一鍵生成企業級資安防禦報告。

---

## 企業系統接入指南 Enterprise Integration

（待開發）PromptShield 設計為可無縫接入任意 LLM-based 應用程式。企業可依據開發階段，選擇以下三種方式將自身系統接入進行安全測試：

### 方法一：靜態配置替換（可以快速驗證）

適用於尚未開發 API 的系統。直接修改 `VICTIM_SCENARIOS`，新增您的系統情境，例如：

```python
"my_system": {
    "name": "企業內部知識庫系統",
    "system_prompt": "你是內部知識庫助理，僅能回答員工的一般問題...",
    "sensitive_keywords": ["資料庫連線字串", "管理員密碼", "API金鑰"]
}
```

### 方法二：串接真實 API 端點（線上服務測試）

適用於已上線或測試環境中的服務。修改 src/victim.py 內的 respond() 方法，直接呼叫您的真實 API：

```python
def respond(self, user_input: str) -> dict:
    import requests
    # 呼叫企業真實系統的 API
    resp = requests.post(
        "[https://your-system.com/api/chat](https://your-system.com/api/chat)",
        json={"message": user_input},
        headers={"Authorization": f"Bearer {YOUR_API_TOKEN}"}
    )
    response_text = resp.json()["reply"]
  
    # 進行資料洩漏偵測
    leaked = self._detect_leakage(response_text)
    return {
        "response": response_text,
        "leaked": len(leaked) > 0,
        "leaked_keywords": leaked
    }
```

### 方法三：CI/CD 流程自動化整合（DevOps）

在每次應用程式版本更新或提示詞修改前，透過腳本在 CI 管道自動執行測試：

```bash
# 若攻擊突破率大於 10%，則中斷部署流程
python run_test.py --scenario my_system --attacks 20 --threshold 0.1
```

## 環境設定與執行

### 1. 系統需求

Python 3.9+
Google Gemini API Key
NVIDIA NIM API Key (用於 Llama 3.3 模型)

### 2. 安裝依賴

```bash
# 建立虛擬環境
python3 -m venv .venv
source .venv/bin/activate  # Windows 環境請使用 .venv\Scripts\activate

# 安裝套件
pip install -r requirements.txt
```

### 3. 設定環境變數

請在專案根目錄建立 .env 檔案，或直接在系統中設定以下環境變數：

```
NVIDIA_API_KEY=your_nvidia_nim_api_key
GEMINI_API_KEY=your_google_api_key
```

### 4. 啟動系統

```bash
streamlit run app.py
```

啟動後系統將開啟瀏覽器，請導航至 http://localhost:8501 操作圖形化介面。

## 專案背景

本專案為「LLM Applications in Cybersecurity」課程之 Proof of Concept (PoC) 專題實作。旨在探討並解決大型語言模型於實際部署時所面臨的 Prompt Injection 安全威脅，透過工程實踐橋接學術研究與企業真實需求。
