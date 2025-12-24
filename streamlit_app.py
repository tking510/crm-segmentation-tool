import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile

st.set_page_config(
    page_title="CRM Segmentation Tool",
    page_icon="",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# カスタムCSS
st.markdown("""
<style>
    /* 全体のフォント */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* ヘッダー */
    .main-header {
        font-size: 2.5rem;
        font-weight: 600;
        color: #1a1a2e;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }
    
    .sub-header {
        font-size: 1rem;
        color: #6b7280;
        margin-bottom: 2rem;
        font-weight: 400;
    }
    
    /* セクションタイトル */
    .section-title {
        font-size: 0.875rem;
        font-weight: 500;
        color: #374151;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 1rem;
    }
    
    /* カード風のコンテナ */
    .upload-container {
        background: #f9fafb;
        border: 1px solid #e5e7eb;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    
    /* ボタンスタイル */
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        padding: 0.75rem 2rem;
        font-weight: 500;
        letter-spacing: 0.025em;
        border-radius: 8px;
        transition: all 0.2s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
    }
    
    /* ダウンロードボタン */
    .stDownloadButton > button {
        background: #1a1a2e;
        color: white;
        border: none;
        font-weight: 500;
        border-radius: 8px;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        font-weight: 500;
        color: #374151;
    }
    
    /* 区切り線 */
    hr {
        border: none;
        height: 1px;
        background: #e5e7eb;
        margin: 2rem 0;
    }
    
    /* ファイルアップローダー */
    .stFileUploader {
        border-radius: 8px;
    }
    
    /* 成功メッセージ */
    .stSuccess {
        background-color: #ecfdf5;
        color: #065f46;
        border-radius: 8px;
    }
    
    /* フッター */
    .footer {
        text-align: center;
        color: #9ca3af;
        font-size: 0.75rem;
        margin-top: 3rem;
        padding: 1rem 0;
        border-top: 1px solid #e5e7eb;
    }
</style>
""", unsafe_allow_html=True)

# ヘッダー
st.markdown('<h1 class="main-header">CRM Segmentation Tool</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">ユーザーデータを条件別に自動振り分け</p>', unsafe_allow_html=True)

st.markdown("---")

# アップロードセクション
col1, col2 = st.columns(2)

with col1:
    st.markdown('<p class="section-title">01 / ユーザー表</p>', unsafe_allow_html=True)
    user_file = st.file_uploader("CSV または Excel", type=["csv", "xlsx", "xls"], key="user", label_visibility="collapsed")

with col2:
    st.markdown('<p class="section-title">02 / ユーザー行動詳細</p>', unsafe_allow_html=True)
    behavior_file = st.file_uploader("CSV または Excel", type=["csv", "xlsx", "xls"], key="behavior", label_visibility="collapsed")

st.markdown("---")

st.markdown('<p class="section-title">03 / 前回のユーザー表（任意）</p>', unsafe_allow_html=True)
prev_file = st.file_uploader("差分比較用", type=["csv", "xlsx", "xls"], key="prev", label_visibility="collapsed")

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
    
    seg1 = df[(df['登録時間'].notna()) & (df['登録経過日数'] == 1) & (df['入金回数タグ'] == 0)]
    results['01_登録翌日_未入金'] = seg1
    
    seg2 = df[(df['登録時間'].notna()) & (df['登録経過日数'] == 2) & (df['入金回数タグ'] == 0)]
    results['02_登録2日後_未入金'] = seg2
    
    seg3 = df[(df['登録時間'].notna()) & (df['登録経過日数'] == 3) & (df['入金回数タグ'] == 0)]
    results['03_登録3日後_未入金'] = seg3
    
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

col_btn = st.columns([1, 2, 1])
with col_btn[1]:
    run_button = st.button("振り分け実行", type="primary", use_container_width=True)

if run_button:
    if user_file is None or behavior_file is None:
        st.error("ユーザー表と行動詳細の両方をアップロードしてください")
    else:
        with st.spinner("処理中..."):
            try:
                df_user = load_file(user_file)
                df_behavior = load_file(behavior_file)
                df_prev = load_file(prev_file) if prev_file else None
                
                results = process_segmentation(df_user, df_behavior, df_prev)
                
                st.success("処理完了")
                
                st.markdown("---")
                st.markdown('<p class="section-title">Results</p>', unsafe_allow_html=True)
                
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                    for name, df in results.items():
                        if len(df) > 0:
                            csv_data = df.to_csv(index=False, encoding='utf-8-sig')
                            zf.writestr(f"{name}.csv", csv_data)
                
                zip_buffer.seek(0)
                
                st.download_button(
                    label="全セグメントをダウンロード（ZIP）",
                    data=zip_buffer,
                    file_name="segments.zip",
                    mime="application/zip",
                    use_container_width=True
                )
                
                st.markdown("---")
                for name, df in results.items():
                    with st.expander(f"{name}  —  {len(df)} 件"):
                        if len(df) > 0:
                            st.dataframe(df, use_container_width=True, hide_index=True)
                            csv = df.to_csv(index=False, encoding='utf-8-sig')
                            st.download_button(
                                label=f"Download {name}.csv",
                                data=csv,
                                file_name=f"{name}.csv",
                                mime="text/csv",
                                key=f"dl_{name}"
                            )
                        else:
                            st.info("該当者なし")
                            
            except Exception as e:
                st.error(f"エラー: {str(e)}")

st.markdown("---")
st.markdown('<p class="footer">CSV・Excel両対応 | ブラウザで完結 | データはサーバーに保存されません</p>', unsafe_allow_html=True)
