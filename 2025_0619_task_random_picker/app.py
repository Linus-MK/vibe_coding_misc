import sqlite3
import random
import click
from flask import Flask, render_template, request, redirect, url_for, jsonify, g

app = Flask(__name__)
app.config['DATABASE'] = 'tasks.db'

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
