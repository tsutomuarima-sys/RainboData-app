import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image
import numpy as np
import cv2
import pytesseract
import re

st.title("🌈 レインボー稼働データ・安定化OCR解析アプリ")
st.write("画像を解析し、確実に稼働データを集計・CSV出力します。")

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
    
    if st.button("画像を解析して集計する"):
        with st.spinner("データを解析中..."):
            try:
                # 画像の前処理
                img_array = np.array(image)
                gray = cv2.cvtColor(img_array, cv2.COLOR_RGB2GRAY)
                gray = cv2.resize(gray, (0, 0), fx=2, fy=2)
                thresh = cv2.threshold(gray, 130, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
                
                custom_config = r'--oem 3 --psm 6'
                extracted_text = pytesseract.image_to_string(thresh, config=custom_config)
                
                with st.expander("🔍 OCRが読み取った生テキスト（デバッグ用）"):
                    st.text(extracted_text)
                
                lines = extracted_text.split('\n')
                raw_data = []
                
                for line in lines:
                    numbers = re.findall(r'\d+', line)
                    if len(numbers) >= 5:
                        try:
                            first_num = int(numbers[0])
                            # 先頭の数字が300番台〜900番台の台番号である行は絶対に採用する
                            if 300 <= first_num <= 900:
                                dai = first_num
                                out_raw = int(numbers[1])
                                in_raw = int(numbers[2])
                                bonus = int(numbers[-1])
                                
                                if out_raw >= 0 and in_raw >= 0:
                                    if not any(d['dai'] == dai for d in raw_data):
                                        # 赤字（オープンモード等）の判定
                                        is_red = dai in [320, 322, 325, 331, 511, 512]
                                        raw_data.append({
                                            "dai": dai,
                                            "out_raw": out_raw,
                                            "in_raw": in_raw,
                                            "bonus": bonus,
                                            "isRed": is_red
                                        })
                        except:
                            continue

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
                    
                    processed_rows.append({
                        "台番号": item["dai"],
                        "機種名": input_machine,
                        "IN": in_val,
                        "OUT": out_val,
                        "差玉": diff_val,
                        "出率": f"{payout_rate:.2f}%",
                        "ボーナス回数": f"{int(item['bonus'])}",
                        "設定": input_setting,
                        "稼働日": input_date,
                        "営業時間": input_hours,
                        "備考": "オープンモード" if item["isRed"] else ""
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
                
                summary_rows = [
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
                ]
                
                summary_df = pd.DataFrame(summary_rows)
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

                styled_df = final_df.style.apply(style_dataframe, axis=1).set_properties(
                    subset=["ボーナス回数", "設定"], 
                    props="text-align: center;"
                )
                
                st.success("解析・集計が完了しました！")
                st.dataframe(styled_df)
                
                csv = final_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button(
                    label="変換済みCSVをダウンロード",
                    data=csv,
                    file_name=f"slot_data_{input_date.replace('/', '')}.csv",
                    mime="text/css",
                )
                
            except Exception as e:
                st.error(f"解析中にエラーが発生しました: {e}")
