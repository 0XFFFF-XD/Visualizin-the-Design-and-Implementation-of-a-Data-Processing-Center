import pandas as pd
import numpy as np
import os
import json
import uuid
import pickle
import threading
import time
from datetime import datetime
import matplotlib.pyplot as plt
import plotly
import plotly.graph_objs as go
import plotly.express as px
from flask import Flask, render_template, request, jsonify, send_from_directory
import atexit
import schedule

app = Flask(__name__)

# 数据目录
DATA_DIR = 'data'
TASKS_FILE = os.path.join(DATA_DIR, 'tasks.pkl')
TASK_LOGS_FILE = os.path.join(DATA_DIR, 'task_logs.pkl')

# 确保数据目录存在
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 任务和日志数据
tasks = []
task_logs = []

# 加载已保存的任务和日志
def load_tasks_and_logs():
    global tasks, task_logs
    try:
        if os.path.exists(TASKS_FILE):
            with open(TASKS_FILE, 'rb') as f:
                tasks = pickle.load(f)
        
        if os.path.exists(TASK_LOGS_FILE):
            with open(TASK_LOGS_FILE, 'rb') as f:
                task_logs = pickle.load(f)
    except Exception as e:
        print(f"加载任务数据失败: {e}")
        tasks = []
        task_logs = []

# 保存任务和日志
def save_tasks_and_logs():
    try:
        with open(TASKS_FILE, 'wb') as f:
            pickle.dump(tasks, f)
        with open(TASK_LOGS_FILE, 'wb') as f:
            pickle.dump(task_logs, f)
    except Exception as e:
        print(f"保存任务数据失败: {e}")

# 程序退出时保存数据
atexit.register(save_tasks_and_logs)

# 主页
@app.route('/')
def index():
    return render_template('index.html')

# 数据源管理
@app.route('/data_sources')
def data_sources():
    return render_template('data_sources.html')

# 数据处理页面
@app.route('/data_processing')
def data_processing():
    return render_template('data_processing.html')

# 可视化页面
@app.route('/visualization')
def visualization():
    return render_template('visualization.html')

# 仪表盘页面
@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

# 任务调度页面
@app.route('/scheduling')
def scheduling():
    return render_template('scheduling.html')

# API: 获取所有数据源
@app.route('/api/data_sources', methods=['GET'])
def get_data_sources():
    try:
        sources = []
        if os.path.exists(DATA_DIR):
            for file in os.listdir(DATA_DIR):
                if file.endswith('.csv'):
                    sources.append({
                        'name': file,
                        'type': 'CSV'
                    })
        return jsonify(sources)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 上传数据
@app.route('/api/upload', methods=['POST'])
def upload_data():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file part'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
        
        if file:
            file.save(os.path.join(DATA_DIR, file.filename))
            return jsonify({'message': 'File uploaded successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取数据预览
@app.route('/api/data/<filename>/preview')
def data_preview(filename):
    try:
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(file_path):
            # 尝试不同的编码方式读取CSV文件
            df = None
            encodings = ['utf-8', 'gbk', 'utf-8-sig', 'latin1']
            for encoding in encodings:
                try:
                    # 使用不同的分隔符尝试读取
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
                except pd.errors.ParserError:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, sep=';')
                        break
                    except:
                        try:
                            df = pd.read_csv(file_path, encoding=encoding, sep='\t')
                            break
                        except:
                            continue
            
            if df is None:
                # 尝试使用错误处理策略读取
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', error_bad_lines=False, warn_bad_lines=False)
                except:
                    return jsonify({'error': '无法读取文件，请检查文件格式是否为标准CSV格式'}), 400
            
            # 确保列名是字符串类型
            df.columns = [str(col) for col in df.columns]
            
            # 处理所有列的数据类型
            for col in df.columns:
                df[col] = df[col].apply(lambda x: x if pd.notna(x) else None)
            
            # 识别数值型列和分类列
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
            
            result = {
                'columns': df.columns.tolist(),
                'data': df.head(50).to_dict('records'),  # 增加数据量
                'info': {
                    'total_rows': len(df),
                    'total_columns': len(df.columns),
                    'numeric_columns': numeric_columns,
                    'categorical_columns': categorical_columns
                }
            }
            
            # 处理可能的NaN值
            for record in result['data']:
                for key in record:
                    if pd.isna(record[key]):
                        record[key] = None
                    # 处理特殊值
                    elif isinstance(record[key], (np.integer, np.floating)):
                        if np.isnan(record[key]) or np.isinf(record[key]):
                            record[key] = None
                    # 转换numpy类型为Python原生类型
                    elif isinstance(record[key], (np.integer)):
                        record[key] = int(record[key])
                    elif isinstance(record[key], (np.floating)):
                        record[key] = float(record[key])
                        
            return jsonify(result)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': '数据加载失败: ' + str(e)}), 500

# API: 获取任务列表
@app.route('/api/tasks', methods=['GET'])
def get_tasks():
    try:
        return jsonify(tasks)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 创建任务
@app.route('/api/tasks', methods=['POST'])
def create_task():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        task = {
            'id': str(uuid.uuid4()),  # 使用UUID作为唯一标识符
            'name': data.get('name'),
            'dataSource': data.get('dataSource'),
            'operations': data.get('operations', []),
            'schedule': data.get('schedule', 'once'),
            'scheduleTime': data.get('scheduleTime'),
            'description': data.get('description', ''),
            'status': 'scheduled',
            'createdAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'nextRun': calculate_next_run(data.get('schedule'), data.get('scheduleTime')),
            'dependencies': data.get('dependencies', []),  # 任务依赖
            'outputFilename': data.get('outputFilename', f"processed_{data.get('dataSource')}")  # 输出文件名
        }
        
        tasks.append(task)
        save_tasks_and_logs()  # 保存到文件
        return jsonify(task), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 删除任务
@app.route('/api/tasks/<string:task_id>', methods=['DELETE'])
def delete_task(task_id):
    try:
        global tasks
        tasks = [task for task in tasks if task['id'] != task_id]
        save_tasks_and_logs()  # 保存到文件
        return jsonify({'message': 'Task deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 执行任务
@app.route('/api/tasks/<string:task_id>/run', methods=['POST'])
def run_task(task_id):
    try:
        task = next((t for t in tasks if t['id'] == task_id), None)
        if not task:
            return jsonify({'error': 'Task not found'}), 404
        
        # 检查依赖任务是否完成
        for dep_id in task.get('dependencies', []):
            dep_task = next((t for t in tasks if t['id'] == dep_id), None)
            if dep_task and dep_task['status'] != 'completed':
                return jsonify({'error': f'依赖任务 {dep_task["name"]} 尚未完成'}), 400
        
        # 更新任务状态
        task['status'] = 'running'
        save_tasks_and_logs()  # 保存到文件
        
        # 在后台线程中执行任务
        thread = threading.Thread(target=execute_task, args=(task,))
        thread.start()
        
        return jsonify({'message': 'Task started successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 获取任务日志
@app.route('/api/task_logs', methods=['GET'])
def get_task_logs():
    try:
        return jsonify(task_logs)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# 计算下次执行时间
def calculate_next_run(schedule, schedule_time=None):
    now = datetime.now()
    if schedule == 'hourly':
        # 下一个小时
        next_run = now.replace(minute=0, second=0, microsecond=0)
        next_run = next_run.replace(hour=next_run.hour + 1)
    elif schedule == 'daily':
        # 明天指定时间或默认时间
        next_run = now.replace(hour=int(schedule_time.split(':')[0]) if schedule_time else 2, 
                              minute=int(schedule_time.split(':')[1]) if schedule_time else 0,
                              second=0, microsecond=0)
        if next_run <= now:
            next_run = next_run.replace(day=next_run.day + 1)
    elif schedule == 'weekly':
        # 下周指定时间
        next_run = now.replace(hour=int(schedule_time.split(':')[0]) if schedule_time else 9, 
                              minute=int(schedule_time.split(':')[1]) if schedule_time else 0,
                              second=0, microsecond=0)
        days_ahead = 7 - next_run.weekday()  # 下周一
        if days_ahead <= 0:
            days_ahead += 7
        next_run = next_run.replace(day=next_run.day + days_ahead)
    elif schedule == 'monthly':
        # 下月指定时间
        next_run = now.replace(hour=int(schedule_time.split(':')[0]) if schedule_time else 9, 
                              minute=int(schedule_time.split(':')[1]) if schedule_time else 0,
                              second=0, microsecond=0)
        if next_run.month == 12:
            next_run = next_run.replace(year=next_run.year + 1, month=1)
        else:
            next_run = next_run.replace(month=next_run.month + 1)
    else:
        # 一次性任务
        next_run = now.replace(second=0, microsecond=0)
        next_run = next_run.replace(minute=next_run.minute + 1)  # 1分钟后执行
    
    return next_run.strftime('%Y-%m-%d %H:%M:%S')

# 执行任务
def execute_task(task):
    start_time = time.time()
    try:
        # 检查依赖任务是否完成
        for dep_id in task.get('dependencies', []):
            dep_task = next((t for t in tasks if t['id'] == dep_id), None)
            if dep_task and dep_task['status'] != 'completed':
                raise Exception(f'依赖任务 {dep_task["name"]} 尚未完成')
        
        # 调用真正的数据处理API
        process_data_request = {
            'filename': task['dataSource'],
            'operations': task['operations'],
            'output_filename': task.get('outputFilename', f"processed_{task['dataSource']}")
        }
        
        # 模拟调用数据处理API
        # 在实际应用中，这里会调用process_data函数或发送HTTP请求到/api/process
        result = process_data_internal(process_data_request)
        
        # 记录执行日志
        duration = time.time() - start_time
        log = {
            'id': str(uuid.uuid4()),
            'taskId': task['id'],
            'taskName': task['name'],
            'executeTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'success',
            'duration': f"{round(duration, 1)}s",
            'message': f'任务执行成功，生成文件: {result.get("filename", "unknown")}'
        }
        
        task_logs.append(log)
        
        # 更新任务状态
        task['status'] = 'completed'
        task['lastRun'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task['nextRun'] = calculate_next_run(task['schedule'], task.get('scheduleTime'))
        
    except Exception as e:
        # 记录失败日志
        duration = time.time() - start_time
        log = {
            'id': str(uuid.uuid4()),
            'taskId': task['id'],
            'taskName': task['name'],
            'executeTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'failed',
            'duration': f"{round(duration, 1)}s",
            'message': str(e)
        }
        
        task_logs.append(log)
        task['status'] = 'failed'
    
    # 保存到文件
    save_tasks_and_logs()

# 内部数据处理函数（模拟API调用）
def process_data_internal(request_data):
    try:
        filename = request_data.get('filename')
        operations = request_data.get('operations', [])
        output_filename = request_data.get('output_filename', f"processed_{filename}")
        
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(file_path):
            raise Exception('File not found')
            
        # 尝试不同的编码方式读取CSV文件
        df = None
        encodings = ['utf-8', 'gbk', 'utf-8-sig', 'latin1']
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except pd.errors.ParserError:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=';')
                    break
                except:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, sep='\t')
                        break
                    except:
                        continue
        
        if df is None:
            try:
                df = pd.read_csv(file_path, encoding='utf-8', error_bad_lines=False, warn_bad_lines=False)
            except:
                raise Exception('无法读取文件，请检查文件格式是否为标准CSV格式')
        
        # 确保列名是字符串类型
        df.columns = [str(col) for col in df.columns]
        
        # 执行数据处理操作
        for operation in operations:
            op_type = operation.get('type')
            if op_type == 'filter':
                column = operation.get('column')
                condition = operation.get('condition')
                value = operation.get('value')
                
                if column in df.columns:
                    if condition == 'equal':
                        df = df[df[column] == value]
                    elif condition == 'not_equal':
                        df = df[df[column] != value]
                    elif condition == 'greater':
                        df = df[df[column] > float(value)]
                    elif condition == 'less':
                        df = df[df[column] < float(value)]
                    elif condition == 'contains':
                        df = df[df[column].astype(str).str.contains(str(value), na=False)]
            elif op_type == 'sort':
                column = operation.get('column')
                ascending = operation.get('ascending', True)
                if column in df.columns:
                    df = df.sort_values(by=column, ascending=ascending, na_position='last')
            elif op_type == 'group':
                column = operation.get('column')
                agg_func = operation.get('agg_func', 'sum')
                if column in df.columns:
                    # 只对数值列进行聚合
                    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    if numeric_cols:
                        grouped = df.groupby(column, as_index=False, dropna=False)
                        if agg_func == 'sum':
                            df = grouped.sum(numeric_only=True)
                        elif agg_func == 'mean':
                            df = grouped.mean(numeric_only=True)
                        elif agg_func == 'count':
                            df = grouped.count().rename(columns={col: f'{col}_count' for col in df.columns if col != column})
                        elif agg_func == 'min':
                            df = grouped.min(numeric_only=True)
                        elif agg_func == 'max':
                            df = grouped.max(numeric_only=True)
            elif op_type == 'rename':
                column = operation.get('column')
                new_name = operation.get('new_name')
                if column in df.columns:
                    df = df.rename(columns={column: new_name})
            elif op_type == 'drop_columns':
                columns = operation.get('columns', [])
                # 确保不删除所有列
                if len(columns) < len(df.columns):
                    df = df.drop(columns=columns, errors='ignore')
        
        # 保存处理后的数据
        processed_filename = f"{output_filename}.csv"
        processed_path = os.path.join(DATA_DIR, processed_filename)
        df.to_csv(processed_path, index=False, encoding='utf-8')
        
        # 处理可能的NaN值
        result_data = df.head(20).to_dict('records')
        for record in result_data:
            for key in record:
                if pd.isna(record[key]):
                    record[key] = None
                # 处理特殊值
                elif isinstance(record[key], (np.integer, np.floating)):
                    if np.isnan(record[key]) or np.isinf(record[key]):
                        record[key] = None
                # 转换numpy类型为Python原生类型
                elif isinstance(record[key], (np.integer)):
                    record[key] = int(record[key])
                elif isinstance(record[key], (np.floating)):
                    record[key] = float(record[key])
        
        return {
            'message': 'Data processed successfully',
            'filename': processed_filename,
            'rows': len(df),
            'columns': len(df.columns),
            'data': result_data
        }
    except Exception as e:
        raise Exception('数据处理失败: ' + str(e))

# API: 处理数据
@app.route('/api/process', methods=['POST'])
def process_data():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的请求数据'}), 400
            
        filename = data.get('filename')
        operations = data.get('operations', [])
        output_filename = data.get('output_filename', f"processed_{filename}")
        
        file_path = os.path.join(DATA_DIR, filename)
        if not os.path.exists(file_path):
            return jsonify({'error': 'File not found'}), 404
            
        # 尝试不同的编码方式读取CSV文件
        df = None
        encodings = ['utf-8', 'gbk', 'utf-8-sig', 'latin1']
        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding)
                break
            except UnicodeDecodeError:
                continue
            except pd.errors.ParserError:
                try:
                    df = pd.read_csv(file_path, encoding=encoding, sep=';')
                    break
                except:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, sep='\t')
                        break
                    except:
                        continue
        
        if df is None:
            try:
                df = pd.read_csv(file_path, encoding='utf-8', error_bad_lines=False, warn_bad_lines=False)
            except:
                return jsonify({'error': '无法读取文件，请检查文件格式是否为标准CSV格式'}), 400
        
        # 确保列名是字符串类型
        df.columns = [str(col) for col in df.columns]
        
        # 执行数据处理操作
        for operation in operations:
            op_type = operation.get('type')
            if op_type == 'filter':
                column = operation.get('column')
                condition = operation.get('condition')
                value = operation.get('value')
                
                if column in df.columns:
                    if condition == 'equal':
                        df = df[df[column] == value]
                    elif condition == 'not_equal':
                        df = df[df[column] != value]
                    elif condition == 'greater':
                        df = df[df[column] > float(value)]
                    elif condition == 'less':
                        df = df[df[column] < float(value)]
                    elif condition == 'contains':
                        df = df[df[column].astype(str).str.contains(str(value), na=False)]
            elif op_type == 'sort':
                column = operation.get('column')
                ascending = operation.get('ascending', True)
                if column in df.columns:
                    df = df.sort_values(by=column, ascending=ascending, na_position='last')
            elif op_type == 'group':
                column = operation.get('column')
                agg_func = operation.get('agg_func', 'sum')
                if column in df.columns:
                    # 只对数值列进行聚合
                    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
                    if numeric_cols:
                        grouped = df.groupby(column, as_index=False, dropna=False)
                        if agg_func == 'sum':
                            df = grouped.sum(numeric_only=True)
                        elif agg_func == 'mean':
                            df = grouped.mean(numeric_only=True)
                        elif agg_func == 'count':
                            df = grouped.count().rename(columns={col: f'{col}_count' for col in df.columns if col != column})
                        elif agg_func == 'min':
                            df = grouped.min(numeric_only=True)
                        elif agg_func == 'max':
                            df = grouped.max(numeric_only=True)
            elif op_type == 'rename':
                column = operation.get('column')
                new_name = operation.get('new_name')
                if column in df.columns:
                    df = df.rename(columns={column: new_name})
            elif op_type == 'drop_columns':
                columns = operation.get('columns', [])
                # 确保不删除所有列
                if len(columns) < len(df.columns):
                    df = df.drop(columns=columns, errors='ignore')
        
        # 保存处理后的数据
        processed_filename = f"{output_filename}.csv"
        processed_path = os.path.join(DATA_DIR, processed_filename)
        df.to_csv(processed_path, index=False, encoding='utf-8')
        
        # 处理可能的NaN值
        result_data = df.head(20).to_dict('records')
        for record in result_data:
            for key in record:
                if pd.isna(record[key]):
                    record[key] = None
                # 处理特殊值
                elif isinstance(record[key], (np.integer, np.floating)):
                    if np.isnan(record[key]) or np.isinf(record[key]):
                        record[key] = None
                # 转换numpy类型为Python原生类型
                elif isinstance(record[key], (np.integer)):
                    record[key] = int(record[key])
                elif isinstance(record[key], (np.floating)):
                    record[key] = float(record[key])
        
        return jsonify({
            'message': 'Data processed successfully',
            'filename': processed_filename,
            'rows': len(df),
            'columns': len(df.columns),
            'data': result_data
        })
    except Exception as e:
        return jsonify({'error': '数据处理失败: ' + str(e)}), 500

# 定时检查任务并执行
def check_and_run_scheduled_tasks():
    while True:
        try:
            now = datetime.now()
            for task in tasks:
                # 检查任务是否处于调度状态且到了执行时间
                if (task['status'] == 'scheduled' or task['schedule'] != 'once') and task.get('nextRun'):
                    next_run = datetime.strptime(task['nextRun'], '%Y-%m-%d %H:%M:%S')
                    if now >= next_run:
                        # 检查依赖任务是否完成
                        dependencies_met = True
                        for dep_id in task.get('dependencies', []):
                            dep_task = next((t for t in tasks if t['id'] == dep_id), None)
                            if dep_task and dep_task['status'] != 'completed':
                                dependencies_met = False
                                break
                        
                        if dependencies_met:
                            # 在后台线程中执行任务
                            task['status'] = 'running'
                            save_tasks_and_logs()
                            thread = threading.Thread(target=execute_task, args=(task,))
                            thread.start()
            
            # 每隔30秒检查一次
            time.sleep(30)
        except Exception as e:
            print(f"检查定时任务时出错: {e}")
            time.sleep(30)

# API: 获取可视化数据
@app.route('/api/visualization/<filename>')
def get_visualization_data(filename):
    try:
        file_path = os.path.join(DATA_DIR, filename)
        if os.path.exists(file_path):
            # 尝试不同的编码方式读取CSV文件
            df = None
            encodings = ['utf-8', 'gbk', 'utf-8-sig', 'latin1']
            for encoding in encodings:
                try:
                    df = pd.read_csv(file_path, encoding=encoding)
                    break
                except UnicodeDecodeError:
                    continue
                except pd.errors.ParserError:
                    try:
                        df = pd.read_csv(file_path, encoding=encoding, sep=';')
                        break
                    except:
                        try:
                            df = pd.read_csv(file_path, encoding=encoding, sep='\t')
                            break
                        except:
                            continue
            
            if df is None:
                try:
                    df = pd.read_csv(file_path, encoding='utf-8', error_bad_lines=False, warn_bad_lines=False)
                except:
                    return jsonify({'error': '无法读取文件，请检查文件格式是否为标准CSV格式'}), 400
            
            # 确保列名是字符串类型
            df.columns = [str(col) for col in df.columns]
            
            # 识别数值型列和分类列
            numeric_columns = df.select_dtypes(include=[np.number]).columns.tolist()
            categorical_columns = df.select_dtypes(include=['object']).columns.tolist()
            
            result = {
                'columns': df.columns.tolist(),
                'data': df.to_dict('records'),
                'info': {
                    'total_rows': len(df),
                    'total_columns': len(df.columns),
                    'numeric_columns': numeric_columns,
                    'categorical_columns': categorical_columns
                }
            }
            
            # 处理可能的NaN值
            for record in result['data']:
                for key in record:
                    if pd.isna(record[key]):
                        record[key] = None
                    # 处理特殊值
                    elif isinstance(record[key], (np.integer, np.floating)):
                        if np.isnan(record[key]) or np.isinf(record[key]):
                            record[key] = None
                    # 转换numpy类型为Python原生类型
                    elif isinstance(record[key], (np.integer)):
                        record[key] = int(record[key])
                    elif isinstance(record[key], (np.floating)):
                        record[key] = float(record[key])
            
            return jsonify(result)
        else:
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': '数据加载失败: ' + str(e)}), 500

if __name__ == '__main__':
    # 加载已保存的任务和日志
    load_tasks_and_logs()
    
    # 启动定时任务检查线程
    scheduler_thread = threading.Thread(target=check_and_run_scheduled_tasks, daemon=True)
    scheduler_thread.start()
    
    app.run(debug=True)