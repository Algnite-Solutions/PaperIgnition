#!/usr/bin/env python3
"""
清理日志文件中的blog内容脚本
删除包含blog文本的行，保留其他重要的日志信息
"""

import re
import sys
from pathlib import Path

def is_blog_content_line(line):
    """
    判断一行是否包含blog内容
    """
    # 检查是否包含blog字段的开始标记
    if "'blog':" in line or '"blog":' in line:
        return True
    
    # 检查是否包含markdown格式的blog内容
    if line.strip().startswith('# ') or line.strip().startswith('## '):
        return True
    
    # 检查是否包含中文blog内容特征
    if '智能体' in line or '大型语言模型' in line or '研究团队' in line:
        return True
    
    # 检查是否包含Figure引用
    if 'Figure ' in line and '.png' in line:
        return True
    
    # 检查是否包含blog相关的长文本内容
    if len(line) > 200 and ('论文' in line or '模型' in line or '研究' in line):
        return True
    
    return False

def cleanup_log_file(input_file, output_file):
    """
    清理日志文件中的blog内容
    """
    print(f"开始清理日志文件: {input_file}")
    
    cleaned_lines = []
    blog_content_started = False
    blog_content_ended = False
    skip_count = 0
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            # 检查是否是blog内容的开始
            if "'blog':" in line or '"blog":' in line:
                blog_content_started = True
                # 保留这一行，但截断blog内容
                if "'blog':" in line:
                    # 找到blog字段的开始位置
                    blog_start = line.find("'blog':")
                    if blog_start != -1:
                        # 保留到blog字段开始，然后添加占位符
                        cleaned_line = line[:blog_start + 7] + " '[BLOG_CONTENT_REMOVED]',\n"
                        cleaned_lines.append(cleaned_line)
                    else:
                        cleaned_lines.append(line)
                else:
                    cleaned_lines.append(line)
                continue
            
            # 如果blog内容已经开始，检查是否结束
            if blog_content_started and not blog_content_ended:
                # 检查是否是blog内容的结束（通常是下一个字段或结束括号）
                if line.strip().endswith("',") and ("'recommendation_reason':" in line or "'relevance_score':" in line or "'blog_abs':" in line):
                    blog_content_ended = True
                    cleaned_lines.append(line)
                    continue
                elif line.strip() == "}" or line.strip().endswith("}"):
                    blog_content_ended = True
                    cleaned_lines.append(line)
                    continue
                else:
                    # 跳过blog内容行
                    skip_count += 1
                    continue
            
            # 检查是否是独立的blog内容行
            if is_blog_content_line(line):
                skip_count += 1
                continue
            
            # 保留其他所有行
            cleaned_lines.append(line)
    
    # 写入清理后的内容
    with open(output_file, 'w', encoding='utf-8') as f:
        f.writelines(cleaned_lines)
    
    print(f"清理完成!")
    print(f"跳过了 {skip_count} 行blog内容")
    print(f"清理后的文件保存为: {output_file}")
    
    return skip_count

def main():
    input_file = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/logs/daily_task_cron.log"
    output_file = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/logs/daily_task_cron_cleaned.log"
    
    if not Path(input_file).exists():
        print(f"错误: 输入文件不存在: {input_file}")
        sys.exit(1)
    
    # 获取原始文件大小
    original_size = Path(input_file).stat().st_size
    print(f"原始文件大小: {original_size / 1024 / 1024:.2f} MB")
    
    # 执行清理
    skip_count = cleanup_log_file(input_file, output_file)
    
    # 获取清理后文件大小
    cleaned_size = Path(output_file).stat().st_size
    print(f"清理后文件大小: {cleaned_size / 1024 / 1024:.2f} MB")
    print(f"节省空间: {(original_size - cleaned_size) / 1024 / 1024:.2f} MB")
    
    # 替换原文件
    print("\n是否要替换原文件? (y/n): ", end="")
    choice = input().lower()
    if choice == 'y':
        Path(output_file).replace(input_file)
        print("原文件已替换")
    else:
        print("原文件保持不变，清理后的文件保存为:", output_file)

if __name__ == "__main__":
    main()
