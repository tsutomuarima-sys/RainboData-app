import streamlit as st
import pandas as pd
from PIL import Image
import io

st.title("🌈 レインボー稼働データ・アップローダー")
st.write("スロットの稼働データ画像をドラッグ＆ドロップしてください。自動で数値化・スプレッドシート用データに変換します！")

# ファイルのアップロード部品
uploaded_file = st.file_uploader("稼働データの画像を選択またはドロップしてください", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    # 画像の表示
    image = Image.open(uploaded_file)
    st.image(image, caption="アップロードされた画像", use_column_width=True)
    
    if st.button("データを処理する"):
        st.info("データを解析・変換中...")
        
        # --- ここに先ほどのルール（10倍化、マイナス判定など）の処理を入れます ---
        # サンプルとして仮のデータを生成します
        processed_data = [
            {"台番号": 318, "機種名": "レインボー★ビンゴ", "OUT": 17690, "IN": 22300, "差玉": 4600, "ボーナス回数": 17, "設定": 4, "稼働日": "2026/08/01", "営業時間": "22時～6時", "備考": ""},
            {"台番号": 320, "機種名": "レインボー★ビンゴ", "OUT": 30790, "IN": 21640, "差玉": -9150, "ボーナス回数": 45, "設定": 4, "稼働日": "2026/08/01", "営業時間": "22時～6時", "備考": "オープンモード"},
            {"台番号": 321, "機種名": "レインボー★ビンゴ", "OUT": 28130, "IN": 24720, "差玉": -3410, "ボーナス回数": 30, "設定": 4, "稼働日": "2026/08/01", "営業時間": "22時～6時", "備考": ""},
        ]
        
        df = pd.DataFrame(processed_data)
        
        st.success("処理が完了しました！")
        st.dataframe(df)
        
        # CSVダウンロードボタン
        csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
        st.download_button(
            label="変換済みCSVをダウンロード",
            data=csv,
            file_name="processed_slot_data.csv",
            mime="text/csv",
        )