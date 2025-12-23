# CRM CSV自動振り分けツール

ユーザーデータを条件別にセグメント分けするWebツール

## 使い方
1. ユーザー表とユーザー行動詳細をアップロード
2. 「振り分け実行」ボタンをクリック
3. ZIPでダウンロード

## セグメント一覧
- segment_01_payment: 登録翌日、未入金
- segment_02_heavenshot: 登録2日後、未入金
- segment_03_ticket10: 登録3日後、未入金
- segment_04_cashback: 登録4日後、未入金
- segment_05_vip_lv2: レベル1→2昇格
- segment_06_vip_up: レベルアップ
- segment_07_balance_inactive: 残高あり30日非ログイン
- segment_08_balance_no_bet: 高残高で賭けなし
