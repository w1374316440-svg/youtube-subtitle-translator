import os
import webvtt
from openai import OpenAI

def translate_subtitles(vtt_file_path, api_key, base_url="https://api.deepseek.com"):
    """
    Parses a VTT file, translates the content using DeepSeek API, 
    and returns a formatted string (Original + Translation).
    """
    if not os.path.exists(vtt_file_path):
        raise FileNotFoundError(f"File not found: {vtt_file_path}")

    print("Parsing subtitles...")
    try:
        captions = webvtt.read(vtt_file_path)
    except Exception:
        # Fallback if webvtt is not installed or fails, but we expect it to be installed
        # For now let's assume it works or fail hard so user installs deps
        print("Error reading VTT file. Please ensure 'webvtt-py' is installed.")
        return None

    client = OpenAI(api_key=api_key, base_url=base_url)

    translated_content = []
    
    # Prepare batches to reduce API calls and improve context
    batch_size = 20
    caption_batch = []
    
    # 用于去重的集合
    seen_texts = set()
    
    total_captions = len(captions)
    print(f"原始字幕行数: {total_captions}")

    for i, caption in enumerate(captions):
        # 清理文本：移除换行符和多余空格
        text = caption.text.replace('\n', ' ').strip()
        
        # 跳过空行或仅包含时间戳的行
        if not text or text.strip() == '':
            continue
            
        # 跳过纯时间戳行（YouTube VTT经常有这种重复）
        if text.replace('.', '').replace(':', '').replace(' ', '').isdigit():
            continue
            
        # 去重：跳过已经处理过的相同文本
        if text in seen_texts:
            continue
        seen_texts.add(text)
        
        caption_batch.append(text)

        if len(caption_batch) >= batch_size or i == total_captions - 1:
            # Process batch
            print(f"Translating batch {i - len(caption_batch) + 2} to {i + 1}...")
            
            original_text_block = "\n".join(caption_batch)
            
            try:
                response = client.chat.completions.create(
                    model="deepseek-chat",
                    messages=[
                        {"role": "system", "content": "You are a professional translator. Translate the following subtitle lines into Simplified Chinese. Maintain the line-by-line structure. Output ONLY the translated lines, one per original line. Do not add any intro or outro."},
                        {"role": "user", "content": original_text_block}
                    ],
                    stream=False
                )
                
                translated_response = response.choices[0].message.content.strip()
                translated_block = translated_response.split('\n')
                
                # 清理翻译结果：移除空行
                translated_block = [line.strip() for line in translated_block if line.strip()]
                
                # Align translations with originals
                # 改进的匹配逻辑，处理行数不匹配的情况
                if len(translated_block) != len(caption_batch):
                    print(f"⚠️  警告: 批次行数不匹配 (原文: {len(caption_batch)}, 翻译: {len(translated_block)})")
                    
                    # 如果翻译行数较少，重复使用最后一行
                    if len(translated_block) < len(caption_batch):
                        while len(translated_block) < len(caption_batch):
                            translated_block.append(translated_block[-1] if translated_block else "[翻译缺失]")
                    
                    # 如果翻译行数较多，截取前面的行
                    elif len(translated_block) > len(caption_batch):
                        translated_block = translated_block[:len(caption_batch)]
                
                # 添加处理后的内容
                for j, orig in enumerate(caption_batch):
                    trans = translated_block[j] if j < len(translated_block) else "[翻译缺失]"
                    translated_content.append(f"> {orig}\n{trans}\n")

            except Exception as e:
                print(f"Error translating batch: {e}")
                # Fallback: keep original only
                for orig in caption_batch:
                    translated_content.append(f"> {orig}\n[Translation Failed]\n")
            
            caption_batch = [] # Reset batch

    # 添加处理统计
    final_content = []
    final_content.append(f"<!-- 处理统计：原始字幕 {total_captions} 行，去重后 {len(seen_texts)} 行 -->")
    final_content.extend(translated_content)
    
    print(f"✅ 翻译完成！处理了 {len(seen_texts)} 行字幕（原始 {total_captions} 行，去重 {total_captions - len(seen_texts)} 行）")
    return "\n".join(final_content)

if __name__ == "__main__":
    # Test
    # You need a dummy vtt file to test this standalone
    pass
