import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image
import json
import google.generativeai as genai

st.title("🌈 レインボー稼働データ・Gemini AI解析アプリ")
st.write("画像をGemini AIのビジョン機能で直接解析し、高精度に稼働データを集計します。")

# --- サイドバー：設定とAPIキー入力 ---
st.sidebar.header("📊 稼働条件 & API設定")

# APIキーの入力欄（StreamlitのSecretsがあれば自動読み込み、なければ手動入力）
api_key_input = st.sidebar.text_input("Gemini APIキー", value=st.secrets.get("GEMINI_API_KEY", ""), type="password")

default_date = datetime.now().date() - timedelta(days=1)
selected_date = st.sidebar.date_input("稼働日", value=default_date)
input_date = selected_date.strftime("%Y/%m/%d")

input_hours = st.sidebar.text_input("営業時間", value="朝11時～翌朝6時")

use_setting = st.sidebar.checkbox("設定を記録する", value=False)
if use_setting:
    input_setting = st.sidebar.number_input("設定", value=4, step=1)

input_machine = st.sidebar.text_input("機種名", value="レインボー★ビンゴ")

# ファイルのアップロード部品
uploaded_file = st.file_uploader("稼働データの画像を選択またはドロップしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption=f"アップロードされた画像: {uploaded_file.name}", use_container_width=True)
    
    if st.button("✨ Gemini AIで画像を解析・集計する"):
        if not api_key_input:
            st.error("サイドバーに Gemini APIキーを入力してください。（Google AI Studioから無料で取得できます）")
            st.stop()
            
        with st.spinner("Gemini AIが画像を読み込んでいます..."):
            try:
                # Gemini APIの設定
                genai.configure(api_key=api_key_input)
                # 高速かつ画像認識に優れたモデルを指定
                model = genai.GenerativeModel('gemini-1.5-flash')
                
                # AIへの指示プロンプト
                prompt = """
                添付された稼働データの画像から、各台のデータを読み取ってください。
                出力は必ず以下のJSON形式の配列のみで行い、余計な解説文やマークダウンのバッククォート（```json等）は含めないでください。
                
                フォーマット例:
                [
                  {"dai": 318, "out_raw": 1751, "in_raw": 2056, "bonus": 19},
                  {"dai": 320, "out_raw": 1751, "in_raw": 1807, "bonus": 16}
                ]
                
                ※注意: 
                - dai は台番号（整数）
                - out_raw は「出球」または「OUT」側の数値（整数）
                - in_raw は「入球」または「IN」側の数値（整数）
                - bonus は一番右端のボーナス回数（整数）
                - 画像に写っている全ての台を漏れなく抽出してください。
                """
                
                response = model.generate_content([prompt, image])
                raw_text = response.text.strip()
                
                # マークダウンのコードブロックが含まれている場合のクリーニング
                if raw_text.startswith("```"):
                    raw_text = raw_text.split("```")[1]
                    if raw_text.startswith("json"):
                        raw_text = raw_text[4:]
                raw_text = raw_text.strip()
                
                with st.expander("🔍 Gemini AIが返した生データ（デバッグ用）"):
                    st.text(raw_text)
                
                raw_data = json.loads(raw_text)
                
                if len(raw_data) == 0:
                    st.error("有効なデータを検出できませんでした。")
                    st.stop()

                # 台番号順に並べ替え
                raw_data = sorted(raw_data, key=lambda x: x["dai"])

                processed_rows = []
                for item in raw_data:
                    in_val = item["in_raw"] * 10
                    out_val = item["out_raw"] * 10
                    diff_val = in_val - out_val
                    payout_rate = (out_val / in_val * 100) if in_val > 0 else 0
                    
                    row_data = {
                        "台番号": item["dai"],
                        "機種名": input_machine,
                        "IN": in_val,
                        "OUT": out_val,
                        "差玉": diff_val,
                        "出率": f"{payout_rate:.2f}%",
                        "ボーナス回数": f"{int(item['bonus'])}"
                    }
                    if use_setting:
                        row_data["設定"] = input_setting
                        
                    row_data.update({
                        "稼働日": input_date,
                        "営業時間": input_hours,
                        "備考": ""
                    })
                    processed_rows.append(row_data)
                
                df = pd.DataFrame(processed_rows)
                
                # --- 合計・平均行の算出 ---
                total_in = df["IN"].sum()
                total_out = df["OUT"].sum()
                total_diff = df["差玉"].sum()
                total_rate = (total_out / total_in * 100) if total_in > 0 else 0
                total_bonus = int(df["ボーナス回数"].astype(int).sum())
                
                avg_in = int(df["IN"].mean())
                avg_out = int(df["OUT"].mean())
                avg_diff = int(df["差玉"].mean())
                avg_rate = (avg_out / avg_in * 100) if avg_in > 0 else 0
                avg_bonus = round(df["ボーナス回数"].astype(int).mean(), 1)
                
                summary_row1 = {
                    "台番号": "合計", "機種名": "", "IN": total_in, "OUT": total_out, 
                    "差玉": total_diff, "出率": f"{total_rate:.2f}%", "ボーナス回数": f"{total_bonus}"
                }
                summary_row2 = {
                    "台番号": "平均", "機種名": "", "IN": avg_in, "OUT": avg_out, 
                    "差玉": avg_diff, "出率": f"{avg_rate:.2f}%", "ボーナス回数": f"{avg_bonus}"
                }
                
                if use_setting:
                    summary_row1["設定"] = ""
                    summary_row2["設定"] = ""
                    
                summary_row1.update({"稼働日": "", "営業時間": "", "備考": ""})
                summary_row2.update({"稼働日": "", "営業時間": "", "備考": ""})
                
                summary_df = pd.DataFrame([summary_row1, summary_row2])
                final_df = pd.concat([summary_df[df.columns], df], ignore_index=True)
                
                def style_dataframe(row):
                    styles = [''] * len(row)
                    try:
                        diff_val = row["差玉"]
                        if isinstance(diff_val, (int, float)) and diff_val < 0:
                            styles = ['color: #ff4b4b; font-weight: bold;'] * len(row)
                    except:
                        pass
                    return styles

                center_subsets = ["ボーナス回数"]
                if use_setting:
                    center_subsets.append("設定")

                styled_df = final_df.style.apply(style_dataframe, axis=1).set_properties(
                    subset=center_subsets, 
                    props="text-align: center;"
                )
                
                st.success("Gemini AIによる解析・集計が完了しました！")
                st.dataframe(styled_df)
                
                # --- CSVデータおよびクリップボード用タブ区切りデータの作成 ---
                csv = final_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                tsv_text = final_df.to_csv(index=False, sep='\t')
                
                col1, col2 = st.columns([1, 3])
                with col1:
                    st.download_button(
                        label="📥 変換済みCSVをダウンロード",
                        data=csv,
                        file_name=f"slot_data_{input_date.replace('/', '')}.csv",
                        mime="text/csv",
                    )
                with col2:
                    safe_tsv = tsv_text.replace('\n', '\\n').replace('"', '\\"')
                    copy_button_html = f"""
                    <script>
                    function copyToClipboard() {{
                        const text = `{tsv_text}`;
                        navigator.clipboard.writeText(text).then(function() {{
                            alert("表のデータをクリップボードにコピーしました！スプレッドシートで Ctrl+V で貼り付けられます。");
                        }}, function(err) {{
                            alert("コピーに失敗しました: " + err);
                        }});
                    }}
                    </script>
                    <button onclick="copyToClipboard()" style="
                        background-color: #ffffff;
                        color: #31333F;
                        border: 1px solid #d0d0d0;
                        padding: 0.45rem 0.75rem;
                        font-weight: 400;
                        font-size: 14px;
                        border-radius: 0.375rem;
                        cursor: pointer;
                        display: inline-flex;
                        align-items: center;
                        gap: 4px;
                        height: 38px;
                    ">
                        📋 表をコピー (スプレッドシート用)
                    </button>
                    """
                    st.components.v1.html(copy_button_html, height=50)
                
            except Exception as e:
                st.error(f"解析中にエラーが発生しました: {e}")
