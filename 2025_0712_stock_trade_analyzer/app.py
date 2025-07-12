from flask import Flask, render_template, request, redirect, url_for, flash
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
        flash('ファイルが選択されていません')
        return redirect(request.url)
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません')
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
        flash(f'{upload_type.capitalize()} ファイルのアップロードが成功しました: {filename}')
        return redirect(url_for('view_csv', upload_type=upload_type, filename=filename))
    else:
        flash('許可されていないファイルタイプです。CSVファイルを選択してください。')
        return redirect(url_for('index'))

@app.route('/view/<upload_type>/<filename>')
def view_csv(upload_type, filename):
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], upload_type, secure_filename(filename))

    if not os.path.exists(filepath):
        flash('ファイルが見つかりません。')
        return redirect(url_for('index'))

    try:
        df = None
        if upload_type == 'jotoeki':
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

        else: # upload_type == 'yakujo' など、他のファイル形式
            try:
                df = pd.read_csv(filepath, encoding='utf-8')
            except UnicodeDecodeError:
                df = pd.read_csv(filepath, encoding='shift-jis')
        
        table_html = df.to_html(classes='table table-striped table-hover', index=False, border=0)
        return render_template('view_data.html', table=table_html, filename=filename, upload_type=upload_type)
    except Exception as e:
        flash(f'CSVファイルの読み込み中にエラーが発生しました: {e}')
        return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
