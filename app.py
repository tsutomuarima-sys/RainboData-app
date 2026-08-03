import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image
import json
from google import genai
from google.genai import types

st.title("🌈 レインボー稼働データ・AI自動読み取りアプリ")
st.write("スロットの画像をアップロードすると、AIが自動で数値を読み取り、集計・CSV出力します。")

# --- サイドバー：日付や営業時間の入力設定 ---
st.sidebar.header("📊 稼働条件の設定")

default_date = datetime.now().date() - timedelta(days=1)
selected_date = st.sidebar.date_input("稼働日", value=default_date)
input_date = selected_date.strftime("%Y/%m/%d")

input_hours = st.sidebar.text_input("営業時間", value="朝11時～翌朝6時")
input_setting = st.sidebar.number_input("設定", value=4, step=1)
input_machine = st.sidebar.text_input("機種名", value="レインボー★ビンゴ")

# ファイルのアップロード部品
uploaded_file = st.file_uploader("稼働データの画像を選択またはドロップしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    st.image(image, caption=f"アップロードされた画像: {uploaded_file.name}", use_column_width=True)
    
    if st.button("AIで画像を自動解析して集計する"):
        with st.spinner("AIが画像を解析中...（数秒かかります）"):
            try:
                # APIキーの取得
                api_key = st.secrets.get("GEMINI_API_KEY")
                if not api_key:
                    st.error("StreamlitのSecretsに `GEMINI_API_KEY` が設定されていません。")
                    st.stop()
                
                # 新しい Google GenAI SDK の初期化
                client = genai.Client(api_key=api_key)
                
                # プロンプトの定義（AIに正確な数値を抽出させる）
                prompt = """
                このスロットの稼働データ画像から、台番号ごとのデータを読み取ってください。
                画像には「318」「320」「321」「322」「323」などの台番号、およびそれぞれの数値（IN、OUT、ボーナス回数など）が記載されています。
                赤字やオープンモードなどの特徴がある台は "isRed": true にしてください。
                
                必ず以下のJSON配列フォーマットのみで出力してください（Markdownの ```json ... ``` はつけても構いませんが、JSON以外の余計な文章は一切書かないでください）。
                
                [
                  {"dai": 318, "in_raw": 1769, "out_raw": 2230, "bonus": 17, "isRed": false},
                  ...
                ]
                """
                
                # Gemini 2.0 Flash を使用して画像解析
                response = client.models.generate_content(
                    model='gemini-2.0-flash',
                    contents=[image, prompt]
                )
                
                # 応答テキストからJSON部分を抽出
                text_response = response.text.strip()
                # マークダウンのコードブロックが含まれている場合のクリーニング
                if "```json" in text_response:
                    text_response = text_response.split("```json")[1].split("```")[0].strip()
                elif "```" in text_response:
                    text_response = text_response.split("```")[1].split("```")[0].strip()
                
                raw_data = json.loads(text_response)
                
                processed_rows = []
                for item in raw_data:
                    in_val = int(item["in_raw"]) * 10
                    out_val = int(item["out_raw"]) * 10
                    diff_val = in_val - out_val
                    payout_rate = (out_val / in_val * 100) if in_val > 0 else 0
                    
                    processed_rows.append({
                        "台番号": int(item["dai"]),
                        "機種名": input_machine,
                        "IN": in_val,
                        "OUT": out_val,
                        "差玉": diff_val,
                        "出率": f"{payout_rate:.2f}%",
                        "ボーナス回数": f"{int(item['bonus'])}",
                        "設定": input_setting,
                        "稼働日": input_date,
                        "営業時間": input_hours,
                        "備考": "オープンモード" if item.get("isRed", False) else ""
                    })
                
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
                
                summary_data = pd.DataFrame([
                    {
                        "台番号": "合計", "機種名": "", "IN": total_in, "OUT": total_out, 
                        "差玉": total_diff, "出率": f"{total_rate:.2f}%", "ボーナス回数": f"{total_bonus}",
                        "設定": "", "稼働日": "", "営業時間": "", "備考": ""
                    },
                    {
                        "台番号": "平均", "機種名": "", "IN": avg_in, "OUT": avg_out, 
                        "差玉": avg_diff, "出率": f"{avg_rate:.2f}%", "ボーナス回数": f"{avg_bonus}",
                        "設定": "", "稼働日": "", "営業時間": "", "備考": ""
                    }
                ])
                
                final_df = pd.concat([summary_data, df], ignore_index=True)
                
                # --- 画面表示用のスタイリング（行全体の赤字 ＆ ボーナス・設定のセンター揃え） ---
                def style_dataframe(row):
                    styles = [''] * len(row)
                    try:
                        diff_val = row["差玉"]
                        if isinstance(diff_val, (int, float)) and diff_val < 0:
                            styles = ['color: #ff4b4b; font-weight: bold;'] * len(row)
                    except:
                        pass
                    return styles

                styled_df = final_df.style.apply(style_dataframe, axis=1).set_properties(
                    subset=["ボーナス回数", "設定"], 
                    props="text-align: center;"
                )
                
                st.success("AIによる画像解析・集計が完了しました！")
                st.dataframe(styled_df)
                
                csv = final_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    label="変換済みCSVをダウンロード",
                    data=csv,
                    file_name=f"slot_data_{input_date.replace('/', '')}.csv",
                    mime="text/csv",
                )
                
            except Exception as e:
                st.error(f"解析中にエラーが発生しました: {e}")
                st.info("※もし429エラーや上限エラーが出た場合は、数秒待ってからもう一度ボタンを押すか、APIキーのクォータをご確認ください。")
