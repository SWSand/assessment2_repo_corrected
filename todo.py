import logging
import os
from flask import Flask, jsonify, abort, request, make_response
from flask_mysqldb import MySQL
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

# Set up logging
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger()
logger.setLevel(logging.INFO)
log_directory = 'logs'
os.makedirs(log_directory, exist_ok=True)
log_file_path = os.path.join(log_directory, 'application.log')
file_handler = logging.FileHandler(log_file_path, mode='a')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)
logger.info('This is a sample log message to test.')

app = Flask(__name__)
CORS(app)

# Configuring MySQL database
app.config['MYSQL_HOST'] = os.getenv('MYSQL_DATABASE_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_DATABASE_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_DATABASE_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DATABASE')
app.config['MYSQL_PORT'] = int(os.getenv('MYSQL_DATABASE_PORT'))
mysql = MySQL(app)

connection = mysql.connection
cursor = connection.cursor()

def init_todo_db():
    db_name = os.getenv('MYSQL_DATABASE')
    drop_table = f'DROP TABLE IF EXISTS {db_name}.todos;'
    todos_table = f"""
    CREATE TABLE {db_name}.todos(
    task_id INT NOT NULL AUTO_INCREMENT,
    title VARCHAR(100) NOT NULL,
    description VARCHAR(200),
    is_done BOOLEAN NOT NULL DEFAULT 0,
    PRIMARY KEY (task_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
    """
    data = f"""
    INSERT INTO {db_name}.todos (title, description, is_done)
    VALUES
        ("Learning Linux and AWS", "Finishing all topics", 1 ),
        ("Infra and automation", "Just forgot. Need to revise again.", 0),
        ("CICD", "Learn more", 0);
    """
    cursor.execute(drop_table)
    cursor.execute(todos_table)
    cursor.execute(data)

def log_request_start():
    logging.info('Request started: %s %s', request.method, request.url)

def log_request_end():
    logging.info('Request ended: %s %s', request.method, request.url)

def log_task_operation(operation):
    logging.info('Task %s: %s', operation, request.json['title'])

def log_request_error(error_code):
    logging.error('Request error: %s %s', error_code, request.url)

@app.before_request
def before_request():
    log_request_start()

@app.after_request
def after_request(response):
    log_request_end()
    return response

def get_all_tasks():
    query = "SELECT * FROM todos;"
    cursor.execute(query)
    result = cursor.fetchall()
    tasks = [{'task_id': row[0], 'title': row[1], 'description': row[2], 'is_done': bool(row[3])} for row in result]
    return tasks

def find_task(id):
    query = f"SELECT * FROM todos WHERE task_id={id};"
    cursor.execute(query)
    row = cursor.fetchone()
    task = None
    if row is not None:
        task = {'task_id': row[0], 'title': row[1], 'description': row[2], 'is_done': bool(row[3])}
    return task

def insert_task(title, description):
    insert = f"INSERT INTO todos (title, description) VALUES ('{title}', '{description}');"
    cursor.execute(insert)
    query = f"SELECT * FROM todos WHERE task_id={cursor.lastrowid};"
    cursor.execute(query)
    row = cursor.fetchone()
    return {'task_id': row[0], 'title': row[1], 'description': row[2], 'is_done': bool(row[3])}

def change_task(task):
    update = f"UPDATE todos SET title='{task['title']}', description = '{task['description']}', is_done = {task['is_done']} WHERE task_id= {task['task_id']};"
    cursor.execute(update)
    query = f"SELECT * FROM todos WHERE task_id={task['task_id']};"
    cursor.execute(query)
    row = cursor.fetchone()
    return {'task_id': row[0], 'title': row[1], 'description': row[2], 'is_done': bool(row[3])}

def remove_task(task):
    delete = f"DELETE FROM todos WHERE task_id= {task['task_id']};"
    cursor.execute(delete)
    query = f"SELECT * FROM todos WHERE task_id={task['task_id']};"
    cursor.execute(query)
    row = cursor.fetchone()
    return True if row is None else False

@app.route('/')
def home():
    return "Welcome to the to-do API Service"

@app.route('/todos', methods=['GET'])
def get_tasks():
    try:
        tasks = get_all_tasks()
        return jsonify({'tasks': tasks})
    except Exception as e:
        log_request_error(500)
        return make_response(jsonify({'error': 'Internal server error'}), 500)

@app.route('/todos/<int:task_id>', methods=['GET'])
def get_task(task_id):
    try:
        task = find_task(task_id)
        if task is None:
            abort(404)
        return jsonify({'task found': task})
    except Exception as e:
        log_request_error(500)
        return make_response(jsonify({'error': 'Internal server error'}), 500)

@app.route('/todos', methods=['POST'])
def add_task():
    try:
        if not request.json or not 'title' in request.json:
            abort(400)
        new_task = insert_task(request.json['title'], request.json.get('description', ''))
        log_task_operation('created')
        return jsonify({'newly added task': new_task}), 201
    except Exception as e:
        log_request_error(500)
        return make_response(jsonify({'error': 'Internal server error'}), 500)

@app.route('/todos/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    try:
        task = find_task(task_id)
        if task is None:
            abort(404)
        if not request.json:
            abort(400)
        task['title'] = request.json.get('title', task['title'])
        task['description'] = request.json.get('description', task['description'])
        task['is_done'] = int(request.json.get('is_done', int(task['is_done'])))
        updated_task = change_task(task)
        log_task_operation('updated')
        return jsonify({'updated task': updated_task})
    except Exception as e:
        log_request_error(500)
        return make_response(jsonify({'error': 'Internal server error'}), 500)

@app.route('/todos/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        task = find_task(task_id)
        if task is None:
            abort(404)
        result = remove_task(task)
        if result:
            log_task_operation('deleted')
        else:
            log_request_error(500)
        return jsonify({'result': result})
    except Exception as e:
        log_request_error(500)
        return make_response(jsonify({'error': 'Internal server error'}), 500)

@app.errorhandler(404)
def not_found(error):
    log_request_error(404)
    return make_response(jsonify({'error': 'Not found'}), 404)

@app.errorhandler(400)
def bad_request(error):
    log_request_error(400)
    return make_response(jsonify({'error': 'Bad request'}), 400)

with app.app_context():
    init_todo_db()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=80)
