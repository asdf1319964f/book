from flask import Flask, render_template_string, request, send_from_directory, jsonify
import os
import uuid
import threading
import json
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from werkzeug.utils import secure_filename
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = './uploads'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

task_status = {}

# 修改后的HTML，添加URL输入部分
IMMERSIVE_HTML = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>清新书源检测</title>
    <style>
        :root {
            --primary-color: #6cc6cb;
            --secondary-color: #f4e8c1;
            --text-color: #5a6f73;
            --shadow-color: rgba(108, 198, 203, 0.3);
            --bg-default: linear-gradient(135deg, #e0f7fa, #b2ebf2);
        }

        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }

        html, body {
            height: 100%;
            width: 100%;
            margin: 0;
            padding: 0;
            overflow-x: hidden;
        }

        body {
            font-family: 'Arial', sans-serif;
            color: var(--text-color);
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
            padding: 2vw;
            position: relative; /* 添加position为伪元素定位准备 */
            transition: background 0.5s ease;
        }

        /* 默认背景图片 */
        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            /* 使用本地图片，假设图片位于 static 文件夹 */
            background: url('/static/image.jpg') center/cover no-repeat;
            opacity: 0.9; /* 90%透明度 */
            z-index: -1;
        }

        /* 自定义背景覆盖默认背景 */
        body.custom-bg::before {
            background: url('') center/cover no-repeat;
            opacity: 0.9;
        }

        .main-container {
            background: rgba(255, 255, 255, 0.3);
            padding: clamp(1.5rem, 3vw, 2.5rem);
            border-radius: 1.5rem;
            box-shadow: 0 0.5rem 1.25rem var(--shadow-color);
            border: 1px solid rgba(108, 198, 203, 0.5);
            width: clamp(300px, 90vw, 700px);
            backdrop-filter: blur(8px);
            animation: fadeIn 0.5s ease;
            margin: 2vh auto;
            position: relative; /* 确保内容在背景之上 */
            z-index: 1; /* 确保容器在背景之上 */
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-1.25rem); }
            to { opacity: 1; transform: translateY(0); }
        }

        h1 {
            text-align: center;
            font-size: clamp(1.5rem, 4vw, 2rem);
            margin-bottom: 2rem;
            color: var(--primary-color);
            text-shadow: 0.0625rem 0.0625rem 0.125rem var(--shadow-color);
            font-weight: 600;
        }

        .upload-zone {
            border: 2px dashed rgba(108, 198, 203, 0.7);
            border-radius: 1rem;
            padding: clamp(1rem, 2.5vw, 2rem);
            text-align: center;
            background: rgba(255, 255, 255, 0.2);
            transition: all 0.3s ease;
            display: flex;
            flex-direction: column;
            gap: clamp(0.5rem, 1.5vw, 1rem);
        }

        .upload-zone:hover {
            background: rgba(108, 198, 203, 0.15);
            border-color: var(--secondary-color);
        }

        #file-input, #bg-input {
            display: none;
        }

        .upload-label, .bg-label, .check-url-btn {
            padding: clamp(0.5rem, 1.5vw, 0.625rem) clamp(1rem, 2.5vw, 1.25rem);
            background: rgba(108, 198, 203, 0.8);
            color: white;
            border-radius: 1.5rem;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: clamp(0.875rem, 2vw, 1rem);
            border: none;
            display: inline-flex;
            align-items: center;
            justify-content: center;
        }

        .upload-label:hover, .bg-label:hover, .check-url-btn:hover {
            background: rgba(90, 180, 185, 0.9);
            transform: scale(1.05);
        }

        .url-input {
            width: 100%;
            padding: clamp(0.5rem, 1.5vw, 0.625rem) clamp(0.75rem, 2vw, 0.9375rem);
            border: 1px solid rgba(108, 198, 203, 0.5);
            border-radius: 1.25rem;
            background: rgba(255, 255, 255, 0.3);
            color: var(--text-color);
            font-size: clamp(0.875rem, 2vw, 1rem);
        }

        .url-input:focus {
            outline: none;
            border-color: var(--primary-color);
            background: rgba(255, 255, 255, 0.4);
        }

        #progress-container {
            margin: 1.5rem 0;
            height: 0.375rem;
            background: rgba(108, 198, 203, 0.1);
            border-radius: 0.1875rem;
            overflow: hidden;
        }

        #progress-bar {
            width: 0%;
            height: 100%;
            background: var(--primary-color);
            transition: width 0.5s ease;
        }

        #status {
            text-align: center;
            margin: 1rem 0;
            font-size: clamp(0.875rem, 2vw, 1rem);
            color: var(--text-color);
            text-shadow: 0 0 0.125rem rgba(255, 255, 255, 0.5);
        }

        .results-panel {
            display: none;
            margin-top: 2rem;
            padding-top: 1.5rem;
            border-top: 1px dashed rgba(108, 198, 203, 0.5);
        }

        .result-section {
            background: rgba(244, 232, 193, 0.2);
            padding: 1rem;
            border-radius: 0.625rem;
            margin: 1rem 0;
            border: 1px solid rgba(108, 198, 203, 0.3);
        }

        .result-title {
            font-size: clamp(1rem, 2.5vw, 1.2rem);
            margin-bottom: 0.8rem;
            color: var(--primary-color);
            display: flex;
            align-items: center;
        }

        .result-title::before {
            content: '✿';
            margin-right: 0.5rem;
        }

        .download-btn {
            padding: clamp(0.5rem, 1.5vw, 0.625rem) clamp(0.75rem, 2vw, 1rem);
            background: rgba(108, 198, 203, 0.8);
            color: white;
            border-radius: 1.25rem;
            text-decoration: none;
            transition: all 0.3s ease;
            margin-top: 0.5rem;
            font-size: clamp(0.875rem, 2vw, 1rem);
            display: inline-flex;
            align-items: center;
        }

        .download-btn:hover {
            background: rgba(90, 180, 185, 0.9);
            transform: translateY(-0.125rem);
        }

        /* 响应式设计 - 多断点优化 */
        @media (max-width: 768px) {
            .main-container {
                width: 95vw;
                padding: 2rem;
            }
            h1 {
                font-size: 1.75rem;
            }
            .upload-zone {
                gap: 0.75rem;
            }
        }

        @media (max-width: 480px) {
            .main-container {
                width: 98vw;
                padding: 1.25rem;
            }
            h1 {
                font-size: 1.5rem;
                margin-bottom: 1.5rem;
            }
            .upload-zone {
                padding: 1rem;
                gap: 0.5rem;
            }
            .upload-label, .bg-label, .check-url-btn {
                width: 100%;
                margin: 0.25rem 0;
            }
            .url-input {
                margin: 0.25rem 0;
            }
            .results-panel {
                margin-top: 1.5rem;
                padding-top: 1rem;
            }
            .result-section {
                padding: 0.75rem;
            }
        }

        @media (min-width: 1200px) {
            .main-container {
                max-width: 800px;
                padding: 3rem;
            }
            h1 {
                font-size: 2.25rem;
            }
            .upload-zone {
                padding: 2.5rem;
            }
        }
    </style>
</head>
<body>
    <div class="main-container">
        <h1>✿ 清新书源检测 ✿</h1>
        
        <div class="upload-zone">
            <input type="file" id="file-input" accept=".json">
            <label for="file-input" class="upload-label">选择书源文件</label>
            <input type="file" id="bg-input" accept="image/*">
            <label for="bg-input" class="bg-label">自定义背景</label>
            <input type="text" id="url-input" class="url-input" placeholder="输入远程JSON地址">
            <button class="check-url-btn" onclick="checkUrl()">检测远程书源</button>
            <p style="color:var(--text-color);">支持JSON格式 | 最大16MB</p>
        </div>

        <div id="progress-container">
            <div id="progress-bar"></div>
        </div>
        <div id="status">等待操作...</div>

        <div class="results-panel">
            <div class="result-section">
                <div class="result-title">可用书源</div>
                <a id="good-link" class="download-btn" download>下载数据</a>
            </div>
            <div class="result-section">
                <div class="result-title">失效书源</div>
                <a id="error-link" class="download-btn" download>下载数据</a>
            </div>
        </div>
    </div>

    <script>
        let taskId;
        const statusDiv = document.getElementById('status');
        const progressBar = document.getElementById('progress-bar');
        const resultsPanel = document.querySelector('.results-panel');
        const body = document.body;

        document.getElementById('file-input').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            if (file.size > 16 * 1024 * 1024) {
                statusDiv.innerHTML = '<span style="color:#ff5555">文件超过大小限制</span>';
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                statusDiv.textContent = '▰▰▰ 正在上传文件...';
                const response = await fetch('/upload', { method: 'POST', body: formData });
                const data = await response.json();
                
                if (data.status === 'processing') {
                    taskId = data.task_id;
                    startProgressMonitoring();
                } else {
                    statusDiv.innerHTML = `<span style="color:#ff5555">${data.message}</span>`;
                }
            } catch (error) {
                console.error('上传失败:', error);
                statusDiv.innerHTML = '<span style="color:#ff5555">连接服务器失败</span>';
            }
        });

        document.getElementById('bg-input').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const reader = new FileReader();
            reader.onload = (event) => {
                body.style.setProperty('--custom-bg', `url('${event.target.result}')`);
                body.classList.add('custom-bg');
            };
            reader.readAsDataURL(file);
        });

        async function checkUrl() {
            const url = document.getElementById('url-input').value.trim();
            if (!url) {
                statusDiv.innerHTML = '<span style="color:#ff5555">请输入URL</span>';
                return;
            }

            try {
                statusDiv.textContent = '▰▰▰ 正在获取远程文件...';
                const response = await fetch('/check_url', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ url: url })
                });
                const data = await response.json();
                
                if (data.status === 'processing') {
                    taskId = data.task_id;
                    startProgressMonitoring();
                } else {
                    statusDiv.innerHTML = `<span style="color:#ff5555">${data.message}</span>`;
                }
            } catch (error) {
                console.error('URL检查失败:', error);
                statusDiv.innerHTML = '<span style="color:#ff5555">连接服务器失败</span>';
            }
        }

        async function startProgressMonitoring() {
            const checkProgress = async () => {
                try {
                    const response = await fetch(`/progress/${taskId}`);
                    const data = await response.json();
                    
                    if (data.status === 'completed') {
                        progressBar.style.width = '100%';
                        statusDiv.textContent = '✓ 检测完成';
                        showResults();
                    } else if (data.status === 'processing') {
                        const progress = (data.processed / data.total) * 100;
                        progressBar.style.width = `${progress}%`;
                        statusDiv.textContent = `▰ ${data.processed}/${data.total} 检测中 (${Math.round(progress)}%)`;
                        setTimeout(checkProgress, 500);
                    } else if (data.status === 'error') {
                        statusDiv.innerHTML = `<span style="color:#ff5555">${data.message}</span>`;
                    }
                } catch (error) {
                    console.error('获取进度失败:', error);
                    statusDiv.innerHTML = '<span style="color:#ff5555">进度更新失败</span>';
                }
            };
            checkProgress();
        }

        function showResults() {
            document.getElementById('good-link').href = `/download/${taskId}/good.json`;
            document.getElementById('error-link').href = `/download/${taskId}/error.json`;
            resultsPanel.style.display = 'block';
        }
    </script>
</body>
</html>
'''

class BookChecker:
    def __init__(self, config_path=None, url=None):
        print(f"初始化 BookChecker，配置文件路径: {config_path}, URL: {url}")
        self.books = self._load_books(config_path, url)
        
    def _load_books(self, config_path, url):
        try:
            if url:  # 如果提供了URL
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
                }
                response = requests.get(url, headers=headers, timeout=10, verify=False)
                response.raise_for_status()
                books = response.json()
            elif config_path:  # 如果提供了本地文件路径
                with open(config_path, 'r', encoding='utf-8') as f:
                    books = json.load(f)
            else:
                raise ValueError("必须提供配置文件路径或URL")

            if not isinstance(books, list):
                raise ValueError("书源必须是列表格式")
            print(f"成功加载书源数量: {len(books)}")
            return books
        except Exception as e:
            raise ValueError(f"加载书源失败: {str(e)}")

    def check_source(self, book):
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': '*/*'
        }
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                res = requests.get(
                    book['bookSourceUrl'],
                    headers=headers,
                    timeout=5,
                    verify=False
                )
                if res.status_code == 200:
                    return True
            except Exception as e:
                print(f"检查书源 {book['bookSourceUrl']} 失败 (尝试 {attempt + 1}/{max_attempts}): {str(e)}")
                time.sleep(1)
        return False

    def run_check(self, workers=5):
        total = len(self.books)
        results = {'good': [], 'error': []}
        
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = {executor.submit(self.check_source, book): book for book in self.books}
            for i, future in enumerate(as_completed(futures), 1):
                book = futures[future]
                if future.result():
                    results['good'].append(book)
                else:
                    results['error'].append(book)
                yield i, total
        return results

@app.route('/')
def index():
    return render_template_string(IMMERSIVE_HTML)

@app.route('/upload', methods=['POST'])
def handle_upload():
    print("收到文件上传请求")
    try:
        file = request.files.get('file')
        if not file or not file.filename.endswith('.json'):
            return jsonify({'status': 'error', 'message': '无效文件格式，仅支持 JSON'}), 400
        
        task_id = str(uuid.uuid4())
        task_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        config_path = os.path.join(task_dir, 'config.json')
        file.save(config_path)
        
        task_status[task_id] = {'status': 'processing', 'processed': 0, 'total': 0}
        threading.Thread(target=process_task, args=(task_id, config_path, None), daemon=True).start()
        
        return jsonify({'status': 'processing', 'task_id': task_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'上传失败: {str(e)}'}), 500

@app.route('/check_url', methods=['POST'])
def check_url():
    print("收到URL检查请求")
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({'status': 'error', 'message': 'URL不能为空'}), 400
        
        task_id = str(uuid.uuid4())
        task_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
        os.makedirs(task_dir, exist_ok=True)
        
        task_status[task_id] = {'status': 'processing', 'processed': 0, 'total': 0}
        threading.Thread(target=process_task, args=(task_id, None, url), daemon=True).start()
        
        return jsonify({'status': 'processing', 'task_id': task_id})
    except Exception as e:
        return jsonify({'status': 'error', 'message': f'URL处理失败: {str(e)}'}), 500

def process_task(task_id, config_path, url):
    print(f"开始处理任务: {task_id}")
    try:
        checker = BookChecker(config_path=config_path, url=url)
        task_status[task_id]['total'] = len(checker.books)
        
        for processed, total in checker.run_check(workers=5):
            task_status[task_id]['processed'] = processed
        
        results = {'good': [], 'error': []}
        for book in checker.books:
            if checker.check_source(book):
                results['good'].append(book)
            else:
                results['error'].append(book)
        
        save_results(task_id, results)
        task_status[task_id]['status'] = 'completed'
    except Exception as e:
        task_status[task_id] = {'status': 'error', 'message': str(e)}

def save_results(task_id, results):
    task_dir = os.path.join(app.config['UPLOAD_FOLDER'], task_id)
    for category in ['good', 'error']:
        with open(os.path.join(task_dir, f'{category}.json'), 'w', encoding='utf-8') as f:
            json.dump(results[category], f, ensure_ascii=False, indent=2)

@app.route('/progress/<task_id>')
def get_progress(task_id):
    status = task_status.get(task_id, {'status': 'pending'})
    return jsonify(status)

@app.route('/download/<task_id>/<filename>')
def download(task_id, filename):
    return send_from_directory(
        os.path.join(app.config['UPLOAD_FOLDER'], task_id),
        filename,
        as_attachment=True
    )

if __name__ == '__main__':
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    app.run(host='0.0.0.0', port=5000, debug=True)