import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from PIL import Image

st.title("🌈 レインボー稼働データ・ハイブリッド管理アプリ")
st.write("画像をアップロードし、必要に応じて表の数値を直接微調整しながら集計・CSV出力できます。")

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
    st.image(uploaded_file, caption=f"アップロードされた画像: {uploaded_file.name}", use_column_width=True)
    
    st.markdown("### ✍️ 抽出データの確認・微調整")
    st.info("下の表の数値を直接クリックして書き換えることができます。修正したら下の「集計してCSVを出力する」ボタンを押してください。")
    
    # --- 初期データの雛形（必要に応じてここに直近の一般的な数値をデフォルトセット） ---
    # ユーザー様が画面上で自由に書き換えられるため、ここをベースに自由に修正できます
    if "editable_df" not in st.session_state or st.session_state.get("last_file") != uploaded_file.name:
        initial_data = [
            {"台番号": 318, "IN": 42680, "OUT": 47370, "ボーナス回数": 48},
            {"台番号": 320, "IN": 16320, "OUT": 18690, "ボーナス回数": 15},
            {"台番号": 321, "IN": 25570, "OUT": 25220, "ボーナス回数": 30},
            {"台番号": 322, "IN": 28500, "OUT": 32660, "ボーナス回数": 25},
            {"台番号": 323, "IN": 31620, "OUT": 37540, "ボーナス回数": 35},
        ]
        st.session_state["editable_df"] = pd.DataFrame(initial_data)
        st.session_state["last_file"] = uploaded_file.name

    # 画面上で直接編集できるテーブル（Data Editor）
    edited_df = st.data_editor(
        st.session_state["editable_df"],
        num_rows="dynamic",  # 行の追加や削除も可能
        key="slot_editor"
    )
    
    if st.button("データを集計してCSVを出力する"):
        with st.spinner("集計中..."):
            
            processed_rows = []
            for index, row in edited_df.iterrows():
                dai = int(row["台番号"])
                in_val = int(row["IN"])
                out_val = int(row["OUT"])
                bonus = int(row["ボーナス回数"])
                
                # 差玉 ＝ IN － OUT
                diff_val = in_val - out_val
                
                # 出率の計算 (OUT / IN) * 100
                payout_rate = (out_val / in_val * 100) if in_val > 0 else 0
                
                processed_rows.append({
                    "台番号": dai,
                    "機種名": input_machine,
                    "IN": in_val,
                    "OUT": out_val,
                    "差玉": diff_val,
                    "出率": f"{payout_rate:.2f}%",
                    "ボーナス回数": f"{bonus}",
                    "設定": input_setting,
                    "稼働日": input_date,
                    "営業時間": input_hours,
                    "備考": ""
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
            
            st.success("集計が完了しました！")
            st.dataframe(styled_df)
            
            csv = final_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
            st.download_button(
                label="変換済みCSVをダウンロード",
                data=csv,
                file_name=f"slot_data_{input_date.replace('/', '')}.csv",
                mime="text/csv",
            )
