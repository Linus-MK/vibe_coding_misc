import sqlite3
import random
import click
import io
import csv
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify, g, Response, flash

app = Flask(__name__)
app.config['DATABASE'] = 'tasks.db'
app.secret_key = 'your_very_secret_key' # flashメッセージのために必要

# --- Database Setup ---

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    """Closes the database again at the end of the request."""
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    """Initializes the database."""
    db = get_db()
    with app.open_resource('schema.sql', mode='r') as f:
        db.cursor().executescript(f.read())
    db.commit()

@app.cli.command('init-db')
def init_db_command():
    """Creates the database tables."""
    init_db()
    click.echo('Initialized the database.')

# --- Routes ---
@app.route('/')
def index():
    """Main page, displays a random task."""
    db = get_db()
    cur = db.execute('SELECT * FROM tasks ORDER BY RANDOM() LIMIT 1')
    task = cur.fetchone()
    return render_template('index.html', task=task)

# --- Task Management Routes ---
@app.route('/tasks')
def task_list():
    """Show all tasks and a form to add new tasks."""
    db = get_db()
    cur = db.execute('SELECT * FROM tasks ORDER BY id DESC')
    tasks = cur.fetchall()
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/add', methods=['POST'])
def add_task():
    """Add a new task."""
    name = request.form['name']
    prep_time_str = request.form.get('prep_time_seconds')
    # Use default if prep_time is not provided or empty
    prep_time = int(prep_time_str) if prep_time_str else 15
    duration = int(request.form['duration_minutes'])
    url = request.form.get('url')

    db = get_db()
    db.execute('INSERT INTO tasks (name, prep_time_seconds, duration_minutes, url) VALUES (?, ?, ?, ?)',
               (name, prep_time, duration, url))
    db.commit()
    return redirect(url_for('task_list'))

@app.route('/tasks/update/<int:task_id>', methods=['POST'])
def update_task(task_id):
    """Update a task."""
    name = request.form['name']
    prep_time_str = request.form.get('prep_time_seconds')
    prep_time = int(prep_time_str) if prep_time_str else 15
    duration = int(request.form['duration_minutes'])
    url = request.form.get('url')

    db = get_db()
    db.execute(
        'UPDATE tasks SET name = ?, prep_time_seconds = ?, duration_minutes = ?, url = ? WHERE id = ?',
        (name, prep_time, duration, url, task_id)
    )
    db.commit()
    return redirect(url_for('task_list'))

@app.route('/tasks/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """Delete a task."""
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()
    return redirect(url_for('task_list'))

# --- Import/Export Routes ---
@app.route('/tasks/export')
def export_tasks():
    """Export all tasks to a CSV file."""
    db = get_db()
    cur = db.execute('SELECT name, prep_time_seconds, duration_minutes, url FROM tasks ORDER BY id')
    tasks = cur.fetchall()

    # Use Japanese headers as requested
    fieldnames = ['タスク名', '準備時間(秒)', '実行時間(分)', 'URL']
    
    # Use io.StringIO to create an in-memory text file
    si = io.StringIO()
    # Use utf-8-sig to include BOM for Excel compatibility
    si.write('\ufeff') 
    
    writer = csv.writer(si)
    writer.writerow(fieldnames)
    for task in tasks:
        writer.writerow([task['name'], task['prep_time_seconds'], task['duration_minutes'], task['url']])

    return Response(
        si.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition":
                 f"attachment; filename=action-slot-tasks_{datetime.now().strftime('%Y-%m-%d')}.csv"})


@app.route('/tasks/import', methods=['POST'])
def import_tasks():
    """Import tasks from a CSV file, overwriting existing tasks."""
    if 'file' not in request.files:
        flash('ファイルが選択されていません。')
        return redirect(url_for('task_list'))
    
    file = request.files['file']
    if file.filename == '':
        flash('ファイルが選択されていません。')
        return redirect(url_for('task_list'))

    if file:
        try:
            # Use utf-8-sig to handle CSV with BOM
            stream = io.StringIO(file.stream.read().decode("utf-8-sig"), newline=None)
            csv_reader = csv.reader(stream)
            
            header = next(csv_reader)
            expected_header = ['タスク名', '準備時間(秒)', '実行時間(分)', 'URL']
            if header != expected_header:
                flash(f'CSVのヘッダーが正しくありません。期待するヘッダー: {",".join(expected_header)}')
                return redirect(url_for('task_list'))

            new_tasks = []
            for i, row in enumerate(csv_reader, 2): # Start from line 2 for error reporting
                # Skip empty rows
                if not any(field.strip() for field in row):
                    continue
                
                if len(row) != 4:
                    raise ValueError(f'{i}行目: 列の数が正しくありません（4列である必要があります）。')

                if not row[0] or not row[2]:
                    raise ValueError(f'{i}行目: タスク名と実行時間は必須です。')
                
                new_tasks.append({
                    'name': row[0],
                    'prep_time': int(row[1]) if row[1] else 15,
                    'duration': int(row[2]),
                    'url': row[3] or None
                })
        except ValueError as e:
            flash(f'データのフォーマットエラー: {e}')
            return redirect(url_for('task_list'))
        except Exception as e:
            flash(f'ファイルの処理中に予期せぬエラーが発生しました: {e}')
            return redirect(url_for('task_list'))
            
        db = get_db()
        # Use transaction
        try:
            with db:
                db.execute('DELETE FROM tasks')
                for task in new_tasks:
                    db.execute(
                        'INSERT INTO tasks (name, prep_time_seconds, duration_minutes, url) VALUES (?, ?, ?, ?)',
                        (task['name'], task['prep_time'], task['duration'], task['url'])
                    )
            flash(f'{len(new_tasks)}件のタスクをインポートしました。')
        except sqlite3.Error as e:
            flash(f'データベースエラー: {e}')
            # No need to rollback, 'with db' handles it
            
    return redirect(url_for('task_list'))

# --- API Routes ---
@app.route('/api/random-task')
def get_random_task():
    """Get a random task from the database."""
    db = get_db()
    cur = db.execute('SELECT * FROM tasks ORDER BY RANDOM() LIMIT 1')
    task = cur.fetchone()
    
    if not task:
        return jsonify({'error': 'No tasks found. Please add tasks first.'}), 404
    
    return jsonify(dict(task))
