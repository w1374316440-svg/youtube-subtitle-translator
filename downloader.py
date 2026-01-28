import yt_dlp
import os
import glob

def download_subtitles(url, output_dir=".", cookie_file=None):
    """
    Downloads subtitles from a YouTube URL using yt-dlp.
    Returns the path to the downloaded .vtt file.
    """
    ydl_opts = {
        'skip_download': True,
        'writesubtitles': True,
        'writeautomaticsub': True,
        'subtitleslangs': ['zh-Hans', 'zh-Hant', 'zh', 'en'],  # Prioritize Chinese, then English
        'subtitlesformat': 'vtt',
        'outtmpl': os.path.join(output_dir, '%(id)s.%(ext)s'), # Use ID to avoid filename issues
        'quiet': True,
    }

    # 如果提供了 cookie 文件，添加到选项中
    if cookie_file and os.path.exists(cookie_file):
        ydl_opts['cookiefile'] = cookie_file
        print(f"使用 cookie 文件: {cookie_file}")

    print(f"正在下载字幕: {url}")
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            video_id = info['id']
            video_title = info['title']
            print(f"视频标题: {video_title}")
            
            # 查找下载的 vtt 文件
            pattern = os.path.join(output_dir, f"{video_id}.*.vtt")
            files = glob.glob(pattern)
            
            if not files:
                print("未找到字幕文件。")
                return None, None
            
            subtitle_file = files[0]
            print(f"字幕已下载: {subtitle_file}")
            return subtitle_file, video_title

    except Exception as e:
        print(f"下载字幕时出错: {e}")
        return None, None

if __name__ == "__main__":
    # 测试
    url = input("输入 YouTube URL: ")
    cookie_path = input("输入 cookie 文件路径 (可选，直接回车跳过): ").strip()
    if not cookie_path:
        cookie_path = None
    path, title = download_subtitles(url, cookie_file=cookie_path)
    if path:
        print(f"已下载到: {path}")
