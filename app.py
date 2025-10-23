from flask import Flask, render_template, request, jsonify
import pandas as pd
import json
import os
import numpy as np
from datetime import datetime
import threading
import time

app = Flask(__name__)

# 模拟数据源
DATA_DIR = 'data'
if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

# 模拟任务存储
tasks = []
task_logs = []

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
            
            # 处理所有列的数据类型，将无法解析的值设为None
            for col in df.columns:
                df[col] = df[col].apply(lambda x: x if pd.notna(x) else None)
            
            result = {
                'columns': df.columns.tolist(),
                'data': df.head(20).to_dict('records'),  # 增加预览行数
                'info': {
                    'total_rows': len(df),
                    'total_columns': len(df.columns),
                    'numeric_columns': df.select_dtypes(include=[np.number]).columns.tolist(),
                    'categorical_columns': df.select_dtypes(include=['object']).columns.tolist()
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

# API: 处理数据
@app.route('/api/process', methods=['POST'])
def process_data():
    try:
        data = request.get_json()
        filename = data.get('filename')
        operations = data.get('operations', [])
        
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
                value = operation.get('value')
                # 尝试转换value为合适的类型
                if column in df.columns:
                    # 先尝试按原类型过滤
                    try:
                        df = df[df[column].astype(str) == str(value)]
                    except:
                        df = df[df[column] == value]
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
        
        # 保存处理后的数据
        processed_filename = f"processed_{filename}"
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
    return jsonify(tasks)

# API: 创建任务
@app.route('/api/tasks', methods=['POST'])
def create_task():
    try:
        data = request.get_json()
        task = {
            'id': len(tasks) + 1,
            'name': data.get('name'),
            'dataSource': data.get('dataSource'),
            'operations': data.get('operations', []),
            'schedule': data.get('schedule', 'once'),
            'scheduleTime': data.get('scheduleTime'),
            'description': data.get('description', ''),
            'status': 'scheduled',
            'createdAt': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'nextRun': calculate_next_run(data.get('schedule'), data.get('scheduleTime'))
        }
        
        tasks.append(task)
        return jsonify(task), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# API: 删除任务
@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    global tasks
    tasks = [task for task in tasks if task['id'] != task_id]
    return jsonify({'message': 'Task deleted successfully'})

# API: 执行任务
@app.route('/api/tasks/<int:task_id>/run', methods=['POST'])
def run_task(task_id):
    task = next((t for t in tasks if t['id'] == task_id), None)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    
    # 更新任务状态
    task['status'] = 'running'
    
    # 在后台线程中执行任务
    thread = threading.Thread(target=execute_task, args=(task,))
    thread.start()
    
    return jsonify({'message': 'Task started successfully'})

# API: 获取任务日志
@app.route('/api/task_logs', methods=['GET'])
def get_task_logs():
    return jsonify(task_logs)

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
    try:
        # 模拟任务执行过程
        time.sleep(3)  # 模拟执行时间
        
        # 记录执行日志
        log = {
            'id': len(task_logs) + 1,
            'taskId': task['id'],
            'taskName': task['name'],
            'executeTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'success',
            'duration': f"{round(np.random.uniform(1, 5), 1)}s",
            'message': 'Task executed successfully'
        }
        
        task_logs.append(log)
        
        # 更新任务状态
        task['status'] = 'scheduled'
        task['lastRun'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        task['nextRun'] = calculate_next_run(task['schedule'], task.get('scheduleTime'))
        
    except Exception as e:
        # 记录失败日志
        log = {
            'id': len(task_logs) + 1,
            'taskId': task['id'],
            'taskName': task['name'],
            'executeTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': 'failed',
            'duration': '0s',
            'message': str(e)
        }
        
        task_logs.append(log)
        task['status'] = 'failed'

if __name__ == '__main__':
    app.run(debug=True)