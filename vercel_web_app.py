#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vercel兼容的Web版本 - 使用Flask框架
支持Vercel Serverless Functions部署
"""

from flask import Flask, request, jsonify, render_template_string, Response
import os
import json
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
    <style>
        .panels {
            position: fixed;
            left: 50%;
            transform: translateX(-50%);
            bottom: 20px;
            width: 800px;
            max-width: calc(100vw - 40px);
            display: flex;
            gap: 12px;
            z-index: 9999;
        }
        .subtitle-panel, .deepseek-panel {
            flex: 1;
            background: #fff;
            border: 1px solid #ddd;
            border-radius: 8px;
            display: flex;
            flex-direction: column;
            max-height: 45vh;
            box-shadow: 0 8px 20px rgba(0,0,0,0.12);
        }
        .panel-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 12px;
            background: #f8f9fa;
            border-bottom: 1px solid #ddd;
        }
        .panel-title { font-weight: bold; color: #333; }
        .panel-controls button {
            width: auto;
            padding: 0 8px;
            background: transparent;
            border: none;
            font-size: 18px;
            cursor: pointer;
            color: #333;
        }
        .panel-body {
            flex: 1; overflow: hidden; display: flex; flex-direction: column;
        }
        .subtitle-content {
            flex: 1; overflow-y: auto; padding: 15px; white-space: pre-wrap; font-size: 14px; line-height: 1.6;
        }
        .chat-history {
            flex: 1; overflow-y: auto; padding: 15px; border-bottom: 1px solid #eee;
        }
        .chat-input-area {
            display: flex; padding: 10px; gap: 10px;
        }
        .chat-input-area textarea {
            flex: 1; min-height: 60px; resize: vertical;
        }
        .chat-input-area button {
            width: auto; padding: 10px 20px; background-color: #28a745;
        }
        .minimized .panel-body { display: none; }
        .chat-msg { margin-bottom: 10px; }
        .chat-msg .role { font-weight: bold; margin-bottom: 4px; }
        .chat-msg .content { white-space: pre-wrap; line-height: 1.6; }
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
        
        <button onclick="extractSubtitles()" id="extract_btn" style="background-color:#28a745">提取字幕</button>
        <button onclick="startTranslation()" id="translate_btn">开始翻译</button>
        
        <div id="panels" class="panels" style="display:none;">
          <div class="subtitle-panel" id="subtitle_panel">
            <div class="panel-header">
              <span class="panel-title">字幕内容</span>
              <div class="panel-controls">
                <button onclick="toggleMinimize('subtitle')" title="最小化">—</button>
                <button onclick="closePanel('subtitle')" title="关闭">×</button>
              </div>
            </div>
            <div class="panel-body" id="subtitle_body">
              <div class="subtitle-content" id="subtitle_content"></div>
            </div>
          </div>
          
          <div class="deepseek-panel" id="deepseek_panel">
            <div class="panel-header">
              <span class="panel-title">DeepSeek 交互</span>
              <div class="panel-controls">
                <button onclick="toggleMinimize('deepseek')" title="最小化">—</button>
                <button onclick="closePanel('deepseek')" title="关闭">×</button>
              </div>
            </div>
            <div class="panel-body" id="deepseek_body">
              <div class="chat-history" id="chat_history"></div>
              <div class="chat-input-area">
                <textarea id="deepseek_input" placeholder="输入你的指令，例如：翻译为中文、总结核心观点、解释术语..."></textarea>
                <button onclick="sendToDeepseek()" id="deepseek_send">发送</button>
              </div>
            </div>
          </div>
        </div>
        
        <div id="result" class="result" style="display: none;"></div>
    </div>

    <script>
        document.getElementById('enable_feishu').addEventListener('change', function() {
            const feishuConfig = document.getElementById('feishu_config');
            feishuConfig.style.display = this.checked ? 'block' : 'none';
        });

        let extractedSubtitles = [];
        let chatMessages = [];

        function ensurePanelsVisible() {
            document.getElementById('panels').style.display = 'flex';
        }

        function closePanel(which) {
            const panelId = which === 'subtitle' ? 'subtitle_panel' : 'deepseek_panel';
            const el = document.getElementById(panelId);
            el.style.display = 'none';
            const leftVisible = document.getElementById('subtitle_panel').style.display !== 'none';
            const rightVisible = document.getElementById('deepseek_panel').style.display !== 'none';
            if (!leftVisible && !rightVisible) {
                document.getElementById('panels').style.display = 'none';
            }
        }

        function toggleMinimize(which) {
            const panelId = which === 'subtitle' ? 'subtitle_panel' : 'deepseek_panel';
            document.getElementById(panelId).classList.toggle('minimized');
        }

        async function extractSubtitles() {
            const btn = document.getElementById('extract_btn');
            const videoUrl = document.getElementById('video_url').value.trim();
            const cookieText = document.getElementById('cookie_text').value.trim();
            if (!videoUrl) {
                showResult('请先填写 YouTube 视频链接！', 'error');
                return;
            }

            btn.disabled = true;
            btn.textContent = '提取中...';
            try {
                showResult('正在提取字幕，请稍候...', 'loading');
                const response = await fetch('/api/extract', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ video_url: videoUrl, cookie_text: cookieText })
                });
                const resultJson = await response.json();
                if (!response.ok || !resultJson.success) {
                    showResult(`❌ 提取失败: ${resultJson.error || '未知错误'}`, 'error');
                    return;
                }

                extractedSubtitles = resultJson.subtitles || [];
                document.getElementById('subtitle_content').textContent = extractedSubtitles.join('\\n');
                document.getElementById('subtitle_panel').style.display = 'flex';
                document.getElementById('deepseek_panel').style.display = 'flex';
                ensurePanelsVisible();
                showResult(`✅ 已提取字幕：${resultJson.title || ''}`, 'success');
            } catch (e) {
                showResult(`❌ 网络错误: ${e.message}`, 'error');
            } finally {
                btn.disabled = false;
                btn.textContent = '提取字幕';
            }
        }

        function appendChatMessage(role, content) {
            const historyEl = document.getElementById('chat_history');
            const wrapper = document.createElement('div');
            wrapper.className = 'chat-msg';

            const roleEl = document.createElement('div');
            roleEl.className = 'role';
            roleEl.textContent = role === 'user' ? '你' : 'DeepSeek';

            const contentEl = document.createElement('div');
            contentEl.className = 'content';
            contentEl.textContent = content;

            wrapper.appendChild(roleEl);
            wrapper.appendChild(contentEl);
            historyEl.appendChild(wrapper);
            historyEl.scrollTop = historyEl.scrollHeight;
            return contentEl;
        }

        async function sendToDeepseek() {
            const deepseekKey = document.getElementById('deepseek_key').value.trim();
            const instruction = document.getElementById('deepseek_input').value.trim();
            const sendBtn = document.getElementById('deepseek_send');
            if (!deepseekKey) {
                showResult('请先填写 DeepSeek API 密钥！', 'error');
                return;
            }
            if (!instruction) {
                showResult('请输入你的指令！', 'error');
                return;
            }
            if (!extractedSubtitles.length) {
                showResult('请先点击“提取字幕”获取字幕内容！', 'error');
                return;
            }

            const selection = window.getSelection ? window.getSelection().toString().trim() : '';
            const subtitlesToSend = selection ? [selection] : extractedSubtitles;

            const historyToSend = chatMessages.slice();
            appendChatMessage('user', instruction);
            const assistantEl = appendChatMessage('assistant', '');

            sendBtn.disabled = true;
            sendBtn.textContent = '发送中...';
            document.getElementById('deepseek_input').value = '';

            let assistantText = '';
            try {
                const response = await fetch('/api/deepseek', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        deepseek_key: deepseekKey,
                        instruction,
                        subtitles: subtitlesToSend,
                        history: historyToSend
                    })
                });

                if (!response.ok) {
                    const errJson = await response.json().catch(() => ({}));
                    showResult(`❌ 请求失败: ${errJson.error || '未知错误'}`, 'error');
                    assistantEl.textContent = `请求失败：${errJson.error || '未知错误'}`;
                    return;
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder('utf-8');
                let buffer = '';

                while (true) {
                    const { value, done } = await reader.read();
                    if (done) break;
                    buffer += decoder.decode(value, { stream: true });
                    const parts = buffer.split('\\n\\n');
                    buffer = parts.pop() || '';
                    for (const part of parts) {
                        const line = part.split('\\n').find(l => l.startsWith('data: '));
                        if (!line) continue;
                        const data = line.slice(6).trim();
                        if (data === '[DONE]') {
                            buffer = '';
                            break;
                        }
                        try {
                            const obj = JSON.parse(data);
                            const delta = obj.delta || '';
                            assistantText += delta;
                            assistantEl.textContent = assistantText;
                        } catch (e) {
                        }
                    }
                }

                chatMessages.push({ role: 'user', content: instruction });
                chatMessages.push({ role: 'assistant', content: assistantText });
            } catch (e) {
                showResult(`❌ 网络错误: ${e.message}`, 'error');
                assistantEl.textContent = `网络错误：${e.message}`;
            } finally {
                sendBtn.disabled = false;
                sendBtn.textContent = '发送';
            }
        }
        
        async function startTranslation() {
            const btn = document.getElementById('translate_btn');
            const resultEl = document.getElementById('result');
            
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
            const resultEl = document.getElementById('result');
            resultEl.innerHTML = message;
            resultEl.className = 'result ' + type;
            resultEl.style.display = 'block';
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

@app.route('/api/extract', methods=['POST'])
def extract():
    """提取字幕并返回原始文本"""
    try:
        data = request.get_json()
        video_url = data.get('video_url')
        cookie_text = data.get('cookie_text', '')
        if not video_url:
            return jsonify({'success': False, 'error': '缺少视频链接'}), 400
        
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
        
        vtt_path, video_title = download_subtitles(video_url, TEMP_DIR, cookie_file)
        if not vtt_path:
            return jsonify({'success': False, 'error': '字幕提取失败'}), 500
        
        # 读取字幕内容
        import webvtt
        captions = webvtt.read(vtt_path)
        lines = []
        for caption in captions:
            text = caption.text.replace('\n', ' ').strip()
            if text:
                lines.append(text)
        
        return jsonify({
            'success': True,
            'title': video_title,
            'subtitles': lines
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/deepseek', methods=['POST'])
def deepseek_chat():
    """接收字幕+指令，流式返回答案"""
    try:
        data = request.get_json()
        subtitles = data.get('subtitles', [])
        instruction = data.get('instruction', '')
        api_key = data.get('deepseek_key', '')
        history = data.get('history', [])
        if not subtitles or not instruction or not api_key:
            return jsonify({'success': False, 'error': '缺少参数'}), 400
        
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")
        
        text_block = '\n'.join(subtitles)
        system_prompt = (
            "你是专业字幕助手。请严格按照用户指令处理下方字幕，"
            "直接输出结果，不要多余解释。字幕内容如下：\n\n" + text_block
        )
        
        messages = [{"role": "system", "content": system_prompt}]
        if isinstance(history, list):
            for item in history:
                role = item.get('role')
                content = item.get('content')
                if role in ('user', 'assistant') and isinstance(content, str) and content.strip():
                    messages.append({"role": role, "content": content})
        messages.append({"role": "user", "content": instruction})

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            stream=True
        )
        
        def generate():
            for chunk in response:
                delta = chunk.choices[0].delta.content or ''
                yield f"data: {json.dumps({'delta': delta})}\n\n"
            yield "data: [DONE]\n\n"
        
        return Response(generate(), mimetype='text/event-stream', headers={'Cache-Control': 'no-cache'})
    except Exception as e:
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
