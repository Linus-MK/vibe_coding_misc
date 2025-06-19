import sqlite3
import os
import random
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

# --- Database Setup ---
DATABASE = 'tasks.db'

def get_db():
    """Opens a new database connection if there is none yet for the
    current application context.
    """
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row # This allows accessing columns by name
    return db

def init_db():
    """Initializes the database."""
    with app.app_context():
        db = get_db()
        with open('schema.sql', 'r') as f:
            db.cursor().executescript(f.read())
        db.commit()

def init_db_command():
    """Creates the database tables."""
    if not os.path.exists(DATABASE):
        init_db()
        print('Initialized the database.')

# --- Routes ---
@app.route('/')
def index():
    """Main page, displays a random task."""
    return render_template('index.html')

# --- Task Management Routes ---
@app.route('/tasks')
def task_list():
    """Show all tasks and a form to add new tasks."""
    db = get_db()
    cur = db.execute('SELECT * FROM tasks ORDER BY id DESC')
    tasks = cur.fetchall()
    db.close()
    return render_template('tasks.html', tasks=tasks)

@app.route('/tasks/add', methods=['POST'])
def add_task():
    """Add a new task."""
    name = request.form['name']
    # Use default if prep_time is not provided or empty
    prep_time = request.form.get('prep_time_seconds')
    if not prep_time:
        prep_time = 15
    else:
        prep_time = int(prep_time)
        
    duration = int(request.form['duration_minutes'])
    url = request.form.get('url')

    db = get_db()
    db.execute('INSERT INTO tasks (name, prep_time_seconds, duration_minutes, url) VALUES (?, ?, ?, ?)',
               [name, prep_time, duration, url])
    db.commit()
    db.close()
    return redirect(url_for('task_list'))

@app.route('/tasks/delete/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    """Delete a task."""
    db = get_db()
    db.execute('DELETE FROM tasks WHERE id = ?', [task_id])
    db.commit()
    db.close()
    return redirect(url_for('task_list'))

# --- API Routes ---
@app.route('/api/random-task')
def get_random_task():
    """Get a random task from the database."""
    db = get_db()
    cur = db.execute('SELECT * FROM tasks')
    tasks = cur.fetchall()
    db.close()
    
    if not tasks:
        return jsonify({'error': 'No tasks found. Please add tasks first.'}), 404

    random_task = random.choice(tasks)
    
    # Convert sqlite3.Row to a dictionary to be able to jsonify it
    task_dict = dict(zip([c[0] for c in random_task.keys()], random_task))
    
    return jsonify(task_dict)

if __name__ == '__main__':
    init_db_command()
    app.run(debug=True)
