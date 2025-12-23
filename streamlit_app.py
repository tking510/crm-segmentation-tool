import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile

st.set_page_config(page_title="CRM CSV自動振り分けツール", page_icon="📊", layout="wide")

st.title("📊 CRM CSV自動振り分けツール")
st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("① ユーザー表")
    user_file = st.file_uploader("CSV または Excel", type=["csv", "xlsx", "xls"], key="user")

with col2:
    st.subheader("② ユーザー行動詳細")
    behavior_file = st.file_uploader("CSV または Excel", type=["csv", "xlsx", "xls"], key="behavior")

st.markdown("---")
st.subheader("③ 前回のユーザー表（任意・差分比較用）")
prev_file = st.file_uploader("前回のユーザー表があればアップロード", type=["csv", "xlsx", "xls"], key="prev")

def load_file(uploaded_file):
    if uploaded_file is None:
        return None
    name = uploaded_file.name.lower()
    if name.endswith('.csv'):
        try:
            return pd.read_csv(uploaded_file, encoding='utf-8')
        except:
            uploaded_file.seek(0)
            return pd.read_csv(uploaded_file, encoding='shift-jis')
    else:
        return pd.read_excel(uploaded_file)

def process_segmentation(df_user, df_behavior, df_prev=None):
    results = {}
    
    df_user.columns = df_user.columns.str.strip()
    df_behavior.columns = df_behavior.columns.str.strip()
    
    df_user['登録時間'] = pd.to_datetime(df_user['登録時間'], errors='coerce')
    df_user['ログイン時間'] = pd.to_datetime(df_user['ログイン時間'], errors='coerce')
    
    df_user['現金残高'] = pd.to_numeric(df_user['現金残高'], errors='coerce').fillna(0)
    df_user['レベル'] = pd.to_numeric(df_user['レベル'], errors='coerce').fillna(0)
    df_user['入金回数タグ'] = pd.to_numeric(df_user['入金回数タグ'], errors='coerce').fillna(0)
    df_behavior['賭け金額'] = pd.to_numeric(df_behavior['賭け金額'], errors='coerce').fillna(0)
    
    behavior_agg = df_behavior.groupby('ユーザー名').agg({'賭け金額': 'sum'}).reset_index()
    behavior_agg.columns = ['ユーザー名', '賭け金額合計']
    
    df = df_user.merge(behavior_agg, on='ユーザー名', how='left')
    df['賭け金額合計'] = df['賭け金額合計'].fillna(0)
    
    now = datetime.now()
    df['登録経過日数'] = (now - df['登録時間']).dt.days
    
    # 01: 登録翌日のみ（1日経過〜2日未満）
    seg1 = df[(df['登録時間'].notna()) & (df['登録経過日数'] == 1) & (df['入金回数タグ'] == 0)]
    results['01_登録翌日_未入金'] = seg1
    
    # 02: 登録2日後のみ（2日経過〜3日未満）
    seg2 = df[(df['登録時間'].notna()) & (df['登録経過日数'] == 2) & (df['入金回数タグ'] == 0)]
    results['02_登録2日後_未入金'] = seg2
    
    # 03: 登録3日後のみ（3日経過〜4日未満）
    seg3 = df[(df['登録時間'].notna()) & (df['登録経過日数'] == 3) & (df['入金回数タグ'] == 0)]
    results['03_登録3日後_未入金'] = seg3
    
    # 04: 登録4日後のみ（4日経過〜5日未満）
    seg4 = df[(df['登録時間'].notna()) & (df['登録経過日数'] == 4) & (df['入金回数タグ'] == 0)]
    results['04_登録4日後_未入金'] = seg4
    
    if df_prev is not None:
        df_prev.columns = df_prev.columns.str.strip()
        df_prev['レベル'] = pd.to_numeric(df_prev['レベル'], errors='coerce').fillna(0)
        df_cmp = df.merge(df_prev[['ユーザー名', 'レベル']], on='ユーザー名', how='inner', suffixes=('_now', '_prev'))
        
        seg5 = df_cmp[(df_cmp['レベル_prev'] == 1) & (df_cmp['レベル_now'] == 2)].copy()
        if not seg5.empty:
            seg5 = seg5.drop(columns=['レベル_prev']).rename(columns={'レベル_now': 'レベル'})
        results['05_レベル1から2昇格'] = seg5
        
        seg6 = df_cmp[df_cmp['レベル_now'] > df_cmp['レベル_prev']].copy()
        if not seg6.empty:
            seg6 = seg6.drop(columns=['レベル_prev']).rename(columns={'レベル_now': 'レベル'})
        results['06_レベルアップ'] = seg6
    
    seg7 = df[(df['現金残高'] >= 1) & (df['ログイン時間'].notna()) & ((now - df['ログイン時間']).dt.days >= 30)]
    results['07_残高あり30日非ログイン'] = seg7
    
    seg8 = df[(df['現金残高'] >= 3000) & (df['賭け金額合計'] < 1) & (df['登録時間'].notna()) & (df['登録経過日数'] >= 1)]
    results['08_高残高で賭けなし'] = seg8
    
    return results

st.markdown("---")
if st.button("▶ 振り分け実行", type="primary", use_container_width=True):
    if user_file is None or behavior_file is None:
        st.error("ユーザー表と行動詳細の両方をアップロードしてください")
    else:
        with st.spinner("処理中..."):
            try:
                df_user = load_file(user_file)
                df_behavior = load_file(behavior_file)
                df_prev = load_file(prev_file) if prev_file else None
                
                results = process_segmentation(df_user, df_behavior, df_prev)
                
                st.success("✅ 処理完了！")
                
                st.markdown("---")
                st.subheader("📁 結果")
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for name, df in results.items():
                        if len(df) > 0:
                            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                            zf.writestr(f"{name}.csv", csv_data)
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label="📥 全セグメントをZIPでダウンロード",
                    data=zip_buffer,
                    file_name="segments.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
                st.markdown("---")
                for name, df in results.items():
                    with st.expander(f"{name} ({len(df)}件)"):
                        if len(df) > 0:
                            st.dataframe(df, use_container_width=True)
                            csv = df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(label=f"📥 {name}.csv", data=csv, file_name=f"{name}.csv", mime="text/csv")
                        else:
                            st.info("該当者なし")
                            
            except Exception as e:
                st.error(f"エラー: {str(e)}")

st.markdown("---")
st.caption("CSV・Excel両対応 | ブラウザで完結 | データはサーバーに保存されません")
