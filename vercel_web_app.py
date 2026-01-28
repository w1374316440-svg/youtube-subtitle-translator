#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel兼容的Web版本 - 使用Flask框架
支持Vercel Serverless Functions部署
"""

from flask import Flask, request, jsonify, render_template_string
import os
import json
import tempfile
from downloader import download_subtitles
from translator import translate_subtitles
from feishu_uploader import get_tenant_access_token, upload_file_to_wiki

app = Flask(__name__)

# Vercel兼容的配置
TEMP_DIR = "/tmp" if os.environ.get("VERCEL") else "."

# HTML模板
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>YouTube 字幕翻译助手</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #333;
            text-align: center;
            margin-bottom: 30px;
        }
        .form-group {
            margin-bottom: 20px;
        }
        label {
            display: block;
            margin-bottom: 5px;
            font-weight: bold;
            color: #555;
        }
        input, textarea, select {
            width: 100%;
            padding: 12px;
            border: 1px solid #ddd;
            border-radius: 5px;
            font-size: 14px;
            box-sizing: border-box;
        }
        textarea {
            min-height: 100px;
            resize: vertical;
        }
        button {
            background-color: #007bff;
            color: white;
            padding: 12px 24px;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            cursor: pointer;
            width: 100%;
        }
        button:hover {
            background-color: #0056b3;
        }
        button:disabled {
            background-color: #ccc;
            cursor: not-allowed;
        }
        .result {
            margin-top: 20px;
            padding: 20px;
            background-color: #f8f9fa;
            border-radius: 5px;
            border-left: 4px solid #007bff;
        }
        .error {
            color: #dc3545;
            background-color: #f8d7da;
            border-color: #dc3545;
        }
        .success {
            color: #155724;
            background-color: #d4edda;
            border-color: #28a745;
        }
        .loading {
            text-align: center;
            color: #007bff;
        }
        .config-section {
            background-color: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        .checkbox-group {
            display: flex;
            align-items: center;
            margin-bottom: 10px;
        }
        .checkbox-group input[type="checkbox"] {
            width: auto;
            margin-right: 10px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎬 YouTube 字幕翻译助手</h1>
        
        <div class="config-section">
            <h3>⚙️ 配置设置</h3>
            <div class="form-group">
                <label for="deepseek_key">DeepSeek API 密钥 *</label>
                <input type="password" id="deepseek_key" placeholder="sk-xxxxxxxxxxxxxxxx">
            </div>
            
            <div class="form-group">
                <label for="cookie_text">YouTube Cookie (可选)</label>
                <textarea id="cookie_text" placeholder="PREF=tz=Asia.Shanghai; YSC=xxxxx; ..."></textarea>
            </div>
            
            <div class="checkbox-group">
                <input type="checkbox" id="enable_feishu">
                <label for="enable_feishu">启用飞书上传</label>
            </div>
            
            <div id="feishu_config" style="display: none;">
                <div class="form-group">
                    <label for="feishu_app_id">飞书应用 ID</label>
                    <input type="text" id="feishu_app_id" placeholder="cli_xxxxxxxxxxxxxxxx">
                </div>
                <div class="form-group">
                    <label for="feishu_app_secret">飞书应用密钥</label>
                    <input type="password" id="feishu_app_secret" placeholder="xxxxxxxxxxxxxxxx">
                </div>
                <div class="form-group">
                    <label for="feishu_space_id">飞书空间 ID</label>
                    <input type="text" id="feishu_space_id" placeholder="xxxxxxxxxxxxxxxx">
                </div>
            </div>
        </div>
        
        <div class="form-group">
            <label for="video_url">YouTube 视频链接 *</label>
            <input type="url" id="video_url" placeholder="https://www.youtube.com/watch?v=...">
        </div>
        
        <button onclick="startTranslation()" id="translate_btn">开始翻译</button>
        
        <div id="result" class="result" style="display: none;"></div>
    </div>

    <script>
        // 显示/隐藏飞书配置
        document.getElementById('enable_feishu').addEventListener('change', function() {
            const feishuConfig = document.getElementById('feishu_config');
            feishuConfig.style.display = this.checked ? 'block' : 'none';
        });
        
        async function startTranslation() {
            const btn = document.getElementById('translate_btn');
            const result = document.getElementById('result');
            
            // 获取输入值
            const deepseekKey = document.getElementById('deepseek_key').value.trim();
            const videoUrl = document.getElementById('video_url').value.trim();
            const cookieText = document.getElementById('cookie_text').value.trim();
            const enableFeishu = document.getElementById('enable_feishu').checked;
            
            // 验证必填项
            if (!deepseekKey || !videoUrl) {
                showResult('请填写所有必填项！', 'error');
                return;
            }
            
            // 禁用按钮
            btn.disabled = true;
            btn.textContent = '处理中...';
            
            // 准备数据
            const data = {
                deepseek_key: deepseekKey,
                video_url: videoUrl,
                cookie_text: cookieText,
                enable_feishu: enableFeishu
            };
            
            if (enableFeishu) {
                data.feishu_app_id = document.getElementById('feishu_app_id').value.trim();
                data.feishu_app_secret = document.getElementById('feishu_app_secret').value.trim();
                data.feishu_space_id = document.getElementById('feishu_space_id').value.trim();
                
                if (!data.feishu_app_id || !data.feishu_app_secret || !data.feishu_space_id) {
                    showResult('请填写飞书相关配置！', 'error');
                    btn.disabled = false;
                    btn.textContent = '开始翻译';
                    return;
                }
            }
            
            try {
                showResult('正在处理，请稍候...', 'loading');
                
                const response = await fetch('/api/translate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify(data)
                });
                
                const result = await response.json();
                
                if (response.ok) {
                    if (result.success) {
                        showResult(`✅ 处理完成！<br><br>📄 文件已生成: <a href="${result.download_url}" download="${result.filename}">点击下载</a><br><br>📝 预览:<br><pre>${result.preview}</pre>`, 'success');
                    } else {
                        showResult(`❌ 处理失败: ${result.error}`, 'error');
                    }
                } else {
                    showResult(`❌ 请求失败: ${result.error || '未知错误'}`, 'error');
                }
            } catch (error) {
                showResult(`❌ 网络错误: ${error.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '开始翻译';
            }
        }
        
        function showResult(message, type) {
            const result = document.getElementById('result');
            result.innerHTML = message;
            result.className = 'result ' + type;
            result.style.display = 'block';
        }
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/translate', methods=['POST'])
def translate():
    """API端点：处理翻译请求"""
    try:
        data = request.get_json()
        
        # 验证输入
        if not data or not data.get('video_url') or not data.get('deepseek_key'):
            return jsonify({'success': False, 'error': '缺少必要参数'}), 400
        
        video_url = data['video_url']
        deepseek_key = data['deepseek_key']
        cookie_text = data.get('cookie_text', '')
        enable_feishu = data.get('enable_feishu', False)
        
        # 处理cookie
        cookie_file = None
        if cookie_text:
            cookie_file = os.path.join(TEMP_DIR, 'cookies_netscape.txt')
            with open(cookie_file, 'w') as f:
                f.write("# Netscape HTTP Cookie File\n")
                f.write("# Generated by YouTube Subtitle Translator\n\n")
                cookies = cookie_text.strip().split(';')
                for cookie in cookies:
                    cookie = cookie.strip()
                    if '=' in cookie:
                        name, value = cookie.split('=', 1)
                        f.write(f".youtube.com\tTRUE\t/\tFALSE\t0\t{name.strip()}\t{value.strip()}\n")
        
        # 步骤1: 下载字幕
        print(f"正在下载字幕: {video_url}")
        vtt_path, video_title = download_subtitles(video_url, TEMP_DIR, cookie_file)
        
        if not vtt_path:
            return jsonify({'success': False, 'error': '字幕下载失败'}), 500
        
        # 步骤2: 翻译字幕
        print("正在翻译字幕...")
        translated_content = translate_subtitles(vtt_path, deepseek_key)
        
        if not translated_content:
            return jsonify({'success': False, 'error': '字幕翻译失败'}), 500
        
        # 步骤3: 保存文件
        output_filename = f"{video_title}_翻译版.md"
        # 清理文件名
        output_filename = "".join([c for c in output_filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_', '.')]).rstrip()
        output_path = os.path.join(TEMP_DIR, output_filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"# {video_title} (翻译版)\n\n")
            f.write(f"来源: {video_url}\n\n")
            f.write(translated_content)
        
        # 步骤4: 上传到飞书（可选）
        if enable_feishu:
            feishu_app_id = data.get('feishu_app_id')
            feishu_app_secret = data.get('feishu_app_secret')
            feishu_space_id = data.get('feishu_space_id')
            
            if feishu_app_id and feishu_app_secret and feishu_space_id:
                print("正在上传到飞书...")
                token = get_tenant_access_token(feishu_app_id, feishu_app_secret)
                if token:
                    node_token = upload_file_to_wiki(feishu_space_id, output_path, video_title, token)
                    if node_token:
                        print(f"已上传到飞书，节点: {node_token}")
        
        # 读取文件内容用于预览
        with open(output_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 截取前500字符作为预览
        preview = content[:500] + "..." if len(content) > 500 else content
        
        # 返回成功响应
        return jsonify({
            'success': True,
            'filename': output_filename,
            'download_url': f'/download/{output_filename}',
            'preview': preview
        })
        
    except Exception as e:
        print(f"处理过程中出错: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/download/<filename>')
def download_file(filename):
    """文件下载端点"""
    file_path = os.path.join(TEMP_DIR, filename)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            content = f.read()
        return content, 200, {
            'Content-Type': 'text/markdown',
            'Content-Disposition': f'attachment; filename="{filename}"'
        }
    else:
        return "文件不存在", 404

# Vercel Serverless Functions 需要的导出
if __name__ == '__main__':
    # 本地开发模式
    app.run(debug=True, port=5000)
else:
    # Vercel 生产模式
    pass