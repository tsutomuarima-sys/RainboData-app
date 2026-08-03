import streamlit as st
import pandas as pd
from PIL import Image
import google.generativeai as genai
import json

st.title("🌈 レインボー稼働データ・自動解析アプリ")
st.write("スロットの稼働データ画像をドロップすると、AIが全行のデータを自動で読み取り、10倍化・マイナス判定を行って綺麗に整理します！")

# APIキーの設定（StreamlitのSecretsから自動取得）
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.error("StreamlitのSecretsに 'GEMINI_API_KEY' が設定されていません。")

# ファイルのアップロード部品
uploaded_file = st.file_uploader("稼働データの画像を選択またはドロップしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 画像の表示
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_column_width=True)
    
    if st.button("画像を解析・処理する"):
        with st.spinner("AIが画像を解析中...（数秒かかります）"):
            try:
                # Gemini 2.0 Flashモデルを使用して画像を解析
                model = genai.GenerativeModel("gemini-2.0-flash")
                
                prompt = (
                    "この画像はスロットの稼働データです。\n"
                    "上から順にあるすべての行（318, 320, 321, 322, 323など、画像にあるすべての行）のデータをれぞれ抽出し、"
                    "以下のJSON配列形式（マークダウンの ```json ... ``` なしで、純粋なJSONテキストのみ）で返してください。\n"
                    "【抽出ルール】\n"
                    "- dai: 台番号 (数値)\n"
                    "- out: OUTの数値（カンマを除いた数値）\n"
                    "- in: INの数値（カンマを除いた数値）\n"
                    "- diff: 差玉の数値（カンマを除いた数値）\n"
                    "- bonus: ボーナス回数の数値\n"
                    "- isRed: 赤文字（またはマイナス対象・オープンモード等）の行である場合は true、そうでなければ false\n\n"
                    "出力例:\n"
                    '[{"dai": 318, "out": 1769, "in": 2230, "diff": 460, "bonus": 17, "isRed": false}, '
                    '{"dai": 320, "out": 3079, "in": 2164, "diff": 915, "bonus": 45, "isRed": true}]'
                )
                
                response = model.generate_content([prompt, image])
                raw_text = response.text.strip()
                
                # マークダウン記法が含まれている場合は削除
                raw_text = raw_text.replace("```json", "").replace("```", "").strip()
                data_list = json.loads(raw_text)
                
                # ルールに基づく変換処理（10倍化、赤字行のマイナス化）
                processed_rows = []
                for item in data_list:
                    out_val = item["out"] * 10
                    in_val = item["in"] * 10
                    diff_val = item["diff"] * 10
                    
                    # 赤字行の場合は差玉をマイナスにする
                    if item.get("isRed", False) and diff_val > 0:
                        diff_val = -diff_val
                        
                    processed_rows.append({
                        "台番号": item["dai"],
                        "機種名": "レインボー★ビンゴ",
                        "OUT": out_val,
                        "IN": in_val,
                        "差玉": diff_val,
                        "ボーナス回数": item["bonus"],
                        "設定": 4,
                        "稼働日": "2026/07/31",  # 必要に応じて変更可能
                        "営業時間": "22時～6時",
                        "備考": "オープンモード" if item.get("isRed", False) else ""
                    })
                
                df = pd.DataFrame(processed_rows)
                
                st.success("解析と処理が完了しました！")
                st.dataframe(df)
                
                # CSVダウンロードボタン
                csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    label="変換済みCSVをダウンロード",
                    data=csv,
                    file_name="processed_slot_data.csv",
                    mime="text/csv",
                )
                
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
