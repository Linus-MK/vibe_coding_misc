from flask import Flask, render_template, request, redirect, url_for, flash, make_response
import os
from werkzeug.utils import secure_filename
import pandas as pd

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = 'supersecretkey' # flashメッセージのために必要

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        flash('ファイルが選択されていません', 'danger')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません', 'danger')
        return redirect(request.url)
    if file and file.filename.endswith('.csv'):
        filename = secure_filename(file.filename)
        upload_type = request.form.get('upload_type', 'unknown')
        
        # 保存先ディレクトリを作成
        save_dir = os.path.join(app.config['UPLOAD_FOLDER'], upload_type)
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        filepath = os.path.join(save_dir, filename)
        file.save(filepath)
        flash(f'{upload_type.capitalize()} ファイルのアップロードが成功しました: {filename}', 'success')
        return redirect(url_for('view_csv', upload_type=upload_type, filename=filename))
    else:
        flash('許可されていないファイルタイプです。CSVファイルを選択してください。', 'danger')
        return redirect(url_for('index'))

@app.route('/view/<upload_type>/<filename>')
def view_csv(upload_type, filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], upload_type, secure_filename(filename))

    if not os.path.exists(filepath):
        flash('ファイルが見つかりません。', 'danger')
        return redirect(url_for('index'))

    try:
        df = None
        if upload_type == 'jotoeki':
            # --- ヘッダー情報（対象期間など）の読み込み ---
            header_df = pd.read_csv(filepath, encoding='shift-jis', skiprows=4, nrows=1)
            header_info = {
                'start_date': header_df.columns[0],
                'end_date': header_df.columns[1],
                'count': header_df.columns[2]
            }

            # 譲渡益税明細の特殊なフォーマットに対応
            column_names = [
                'ticker_code', 'name', 'cancellation_category', 'contract_date', 
                'quantity', 'transaction_type', 'delivery_date', 'sale_price', 
                'commission', 'acquisition_date', 'acquisition_price', 'profit_loss'
            ]
            df = pd.read_csv(filepath, encoding='shift-jis', skiprows=21, header=None, names=column_names, dtype=str)
            
            # データクレンジング
            df = df.dropna(how='all') # 全ての列がNaNの行を削除
            df['ticker_code'] = df['ticker_code'].str.strip()
            df['quantity'] = df['quantity'].str.replace('株', '').str.replace(',', '').astype(int)
            for col in ['sale_price', 'commission', 'acquisition_price', 'profit_loss']:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype(int)

            # --- 損益分析 ---
            analysis_results = {}
            if not df.empty:
                total_pl = df['profit_loss'].sum()
                wins = df[df['profit_loss'] > 0]
                losses = df[df['profit_loss'] < 0]
                win_count = len(wins)
                loss_count = len(losses)
                total_profit = wins['profit_loss'].sum()
                total_loss = abs(losses['profit_loss'].sum())
                
                analysis_results = {
                    'total_pl': f"{total_pl:,.0f} 円",
                    'win_count': win_count,
                    'loss_count': loss_count,
                    'win_rate': f"{(win_count / (win_count + loss_count) * 100):.2f} %" if (win_count + loss_count) > 0 else "0.00 %",
                    'avg_profit': f"{total_profit / win_count:,.0f} 円" if win_count > 0 else "0 円",
                    'avg_loss': f"{total_loss / loss_count:,.0f} 円" if loss_count > 0 else "0 円",
                    'profit_factor': f"{(total_profit / total_loss):.2f}" if total_loss > 0 else "∞",
                }
            
            # --- グラフ用データ ---
            chart_data = None
            if not df.empty:
                # 日付の型をdatetimeに変換
                df['delivery_date'] = pd.to_datetime(df['delivery_date'], format='%Y/%m/%d')
                
                # ヘッダー情報から期間全体のカレンダーを作成
                start_date = pd.to_datetime(header_info['start_date'], format='%Y年%m月%d日')
                end_date = pd.to_datetime(header_info['end_date'], format='%Y年%m月%d日')
                all_dates = pd.date_range(start=start_date, end=end_date, freq='D')

                # 日別損益を集計し、期間全体のカレンダーにマッピング
                daily_pl = df.groupby('delivery_date')['profit_loss'].sum()
                daily_pl_full = daily_pl.reindex(all_dates, fill_value=0)
                
                chart_data = {
                    'labels': daily_pl_full.index.strftime('%Y-%m-%d').tolist(),
                    'data': daily_pl_full.values.tolist(),
                }
            
            # --- 表示用にカラム名を日本語化し、不要な列を削除 ---
            display_df = df.drop(columns=['acquisition_date', 'cancellation_category'])
            display_df = display_df.rename(columns={
                'ticker_code': '銘柄コード',
                'name': '銘柄',
                'contract_date': '約定日',
                'quantity': '数量',
                'transaction_type': '取引',
                'delivery_date': '受渡日',
                'sale_price': '売却/決済金額',
                'commission': '費用',
                'acquisition_price': '取得/新規金額',
                'profit_loss': '損益金額/徴収額'
            })


        elif upload_type == 'yakujo':
            # 約定履歴のフォーマットに対応
            column_names = [
                'contract_date', 'name', 'ticker_code', 'market', 'transaction_type', 
                'period', 'account_type', 'tax_category', 'quantity', 
                'unit_price', 'commission', 'tax', 'delivery_date', 
                'settlement_amount'
            ]
            df = pd.read_csv(filepath, encoding='shift-jis', skiprows=9, header=None, names=column_names, dtype=str)
            display_df = df.copy()

            # データクレンジング
            # 株式取引のデータのみを対象とする（銘柄コードがない行は除外）
            df = df.dropna(subset=['ticker_code'])
            df = df[df['ticker_code'].str.strip() != '']
            display_df = df[df['ticker_code'].str.strip() != '']

            # 不要な文字の削除と型変換
            for col in ['quantity', 'commission', 'tax']:
                df[col] = pd.to_numeric(df[col].str.replace(',', ''), errors='coerce').fillna(0).astype(int)
            df['unit_price'] = pd.to_numeric(df['unit_price'].str.replace(',', ''), errors='coerce').fillna(0)
            df['settlement_amount'] = pd.to_numeric(df['settlement_amount'].str.replace(',', ''), errors='coerce').fillna(0)
            display_df['quantity'] = pd.to_numeric(display_df['quantity'].str.replace(',', ''), errors='coerce').fillna(0).astype(int)
            display_df['commission'] = pd.to_numeric(display_df['commission'].str.replace(',', ''), errors='coerce').fillna(0).astype(int)
            display_df['tax'] = pd.to_numeric(display_df['tax'].str.replace(',', ''), errors='coerce').fillna(0).astype(int)
            display_df['unit_price'] = pd.to_numeric(display_df['unit_price'].str.replace(',', ''), errors='coerce').fillna(0)
            display_df['settlement_amount'] = pd.to_numeric(display_df['settlement_amount'].str.replace(',', ''), errors='coerce').fillna(0)


        else: # その他のファイル形式
            try:
                df = pd.read_csv(filepath, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, encoding='shift-jis')
            display_df = df.copy()
        
        table_html = display_df.to_html(classes='table table-striped table-hover', index=False, border=0)
        return render_template('view_data.html', table=table_html, filename=filename, upload_type=upload_type, 
                               header_info=header_info if 'header_info' in locals() else None,
                               analysis_results=analysis_results if 'analysis_results' in locals() else None,
                               chart_data=chart_data if 'chart_data' in locals() else None)
    except Exception as e:
        flash(f'CSVファイルの読み込み中にエラーが発生しました: {e}', 'danger')
        return redirect(url_for('index'))

@app.route('/analysis/summary/<filename>')
def analysis_summary(filename):
    # 分析対象は譲渡益税明細のみ
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'jotoeki', secure_filename(filename))

    if not os.path.exists(filepath):
        flash('分析対象のファイルが見つかりません。', 'danger')
        return redirect(url_for('index'))

    try:
        column_names = [
            'ticker_code', 'name', 'cancellation_category', 'contract_date', 
            'quantity', 'transaction_type', 'delivery_date', 'sale_price', 
            'commission', 'acquisition_date', 'acquisition_price', 'profit_loss'
        ]
        df = pd.read_csv(filepath, encoding='shift-jis', skiprows=21, header=None, names=column_names, dtype=str)
        df = df.dropna(how='all')
        df['profit_loss'] = pd.to_numeric(df['profit_loss'], errors='coerce').fillna(0).astype(int)
        df['delivery_date'] = pd.to_datetime(df['delivery_date'], format='%Y/%m/%d')

        # 銘柄、日付、取引でグループ化して損益を合計
        summary_df = df.groupby(['ticker_code', 'name', 'delivery_date', 'transaction_type']).agg(
            total_profit_loss=('profit_loss', 'sum')
        ).reset_index()

        # カラム名を日本語化
        summary_df = summary_df.rename(columns={
            'ticker_code': '銘柄コード',
            'name': '銘柄',
            'delivery_date': '受渡日',
            'transaction_type': '取引',
            'total_profit_loss': '合計損益'
        })
        
        # --- ベスト3とワースト3を判定 ---
        # 損益でソートされたコピーを作成
        sorted_df = summary_df.sort_values(by='合計損益', ascending=False).copy()
        
        # 0円の取引は除外してインデックスを取得
        best_indices = sorted_df[sorted_df['合計損益'] > 0].head(3).index
        worst_indices = sorted_df[sorted_df['合計損益'] < 0].tail(3).index

        # 元のDataFrameに'rank'列を追加
        summary_df['rank'] = ''
        summary_df.loc[best_indices, 'rank'] = 'best'
        summary_df.loc[worst_indices, 'rank'] = 'worst'

        # 日付のフォーマットを調整
        summary_df['受渡日'] = summary_df['受渡日'].dt.strftime('%Y-%m-%d')

        # テンプレートに渡すデータを作成
        summary_data = summary_df.to_dict('records')
        # 'rank'列はテーブルのヘッダーには不要なので除外
        summary_columns = [col for col in summary_df.columns if col != 'rank']

        return render_template('analysis_summary.html',
                               filename=filename,
                               summary_data=summary_data,
                               summary_columns=summary_columns,
                               file_type='jotoeki')

    except Exception as e:
        flash(f'集計中にエラーが発生しました: {e}', 'danger')
        return redirect(url_for('index'))


@app.route('/download_summary/<filename>')
def download_summary(filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], 'jotoeki', secure_filename(filename))

    if not os.path.exists(filepath):
        flash('分析対象のファイルが見つかりません。', 'danger')
        return redirect(url_for('index'))

    try:
        column_names = [
            'ticker_code', 'name', 'cancellation_category', 'contract_date',
            'quantity', 'transaction_type', 'delivery_date', 'sale_price',
            'commission', 'acquisition_date', 'acquisition_price', 'profit_loss'
        ]
        df = pd.read_csv(filepath, encoding='shift-jis', skiprows=21, header=None, names=column_names, dtype=str)
        df = df.dropna(how='all')
        df['profit_loss'] = pd.to_numeric(df['profit_loss'], errors='coerce').fillna(0).astype(int)
        df['delivery_date'] = pd.to_datetime(df['delivery_date'], format='%Y/%m/%d')

        summary_df = df.groupby(['ticker_code', 'name', 'delivery_date', 'transaction_type']).agg(
            total_profit_loss=('profit_loss', 'sum')
        ).reset_index()

        summary_df = summary_df.rename(columns={
            'ticker_code': '銘柄コード',
            'name': '銘柄',
            'delivery_date': '受渡日',
            'transaction_type': '取引',
            'total_profit_loss': '合計損益'
        })
        
        # 損益でソート
        summary_df = summary_df.sort_values(by='合計損益', ascending=False)
        
        # 日付のフォーマットを調整
        summary_df['受渡日'] = summary_df['受渡日'].dt.strftime('%Y-%m-%d')

        # CSVデータを作成
        csv_data = summary_df.to_csv(index=False, encoding='utf-8')

        # レスポンスを作成
        response = make_response(csv_data)
        response.headers['Content-Disposition'] = f'attachment; filename=summary_{filename}'
        response.headers['Content-Type'] = 'text/csv; charset=utf-8'

        return response

    except Exception as e:
        flash(f'CSVダウンロード中にエラーが発生しました: {e}', 'danger')
        return redirect(url_for('analysis_summary', filename=filename))


if __name__ == '__main__':
    app.run(debug=True)
