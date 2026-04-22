# -*- coding: utf-8 -*-
"""
Markdown Renderer - Converts Markdown to HTML with compact styling
"""
import re


class MarkdownRenderer:
    """Render Markdown to HTML with custom styling"""
    
    def __init__(self, colors=None, dark_mode=False):
        """
        Initialize renderer with color scheme
        
        Args:
            colors: dict with keys: bg, fg, accent, card_bg, border, text_secondary
            dark_mode: whether dark mode is enabled
        """
        self.colors = colors or self._default_colors()
        self.dark_mode = dark_mode
    
    def _default_colors(self):
        """Default light colors"""
        return {
            'bg': '#f5f5f5',
            'fg': '#1f1f1f',
            'accent': '#0078d4',
            'card_bg': '#ffffff',
            'border': '#e1e1e1',
            'text_secondary': '#666666',
        }
    
    def render(self, markdown_text):
        """Convert Markdown to HTML with styling - 紧凑布局"""
        # CSS样式 - 紧凑布局
        bg_color = self.colors.get('card_bg', '#ffffff')
        text_color = self.colors.get('fg', '#1f1f1f')
        accent_color = self.colors.get('accent', '#0078d4')
        code_bg = '#f6f8fa' if not self.dark_mode else '#2d2d2d'
        border_color = self.colors.get('border', '#e1e1e1')
        
        css = f"""
        <style>
            body {{
                font-family: 'Microsoft YaHei UI', 'Microsoft YaHei', 'Segoe UI', 'Segoe UI Emoji', 'Noto Sans CJK SC', 'Noto Sans SC', Helvetica, Arial, sans-serif;
                font-size: 14px;
                line-height: 1.5;
                color: {text_color};
                background-color: {bg_color};
                margin: 0;
                padding: 15px;
            }}
            h1 {{ font-size: 1.8em; margin: 0.8em 0 0.4em 0; padding-bottom: 0.3em; border-bottom: 1px solid {border_color}; color: {text_color}; }}
            h2 {{ font-size: 1.5em; margin: 0.8em 0 0.4em 0; padding-bottom: 0.3em; border-bottom: 1px solid {border_color}; color: {text_color}; }}
            h3 {{ font-size: 1.25em; margin: 0.6em 0 0.3em 0; color: {text_color}; }}
            h4, h5, h6 {{ font-size: 1em; margin: 0.5em 0 0.2em 0; color: {text_color}; }}
            p {{ margin: 0.4em 0; }}
            code {{
                background-color: {code_bg};
                padding: 0.2em 0.4em;
                border-radius: 3px;
                font-family: 'Cascadia Mono', Consolas, 'DejaVu Sans Mono', 'Liberation Mono', Menlo, monospace;
                font-size: 0.9em;
            }}
            pre {{
                background-color: {code_bg};
                padding: 10px;
                border-radius: 6px;
                overflow-x: auto;
                margin: 0.5em 0;
                line-height: 1.4;
            }}
            pre code {{ background-color: transparent; padding: 0; }}
            a {{ color: {accent_color}; text-decoration: none; }}
            a:hover {{ text-decoration: underline; }}
            ul, ol {{ margin: 0.3em 0; padding-left: 2em; }}
            li {{ margin: 0.15em 0; }}
            table {{ border-collapse: collapse; margin: 0.5em 0; }}
            th, td {{ border: 1px solid {border_color}; padding: 6px 10px; text-align: left; }}
            th {{ background-color: {code_bg}; }}
            blockquote {{
                border-left: 4px solid {accent_color};
                padding: 0 0 0 1em;
                margin: 0.5em 0;
                color: {self.colors.get('text_secondary', '#666666')};
            }}
            hr {{ border: none; border-top: 1px solid {border_color}; margin: 1em 0; }}
        </style>
        """
        
        html = markdown_text
        
        # 移除图片
        html = re.sub(r'!\[([^\]]*)\]\([^\)]+\)', r'[\1]', html)
        
        # 转换代码块
        def replace_code_block(match):
            lang = match.group(1) or ''
            code = match.group(2)
            code = code.replace('<', '&lt;').replace('>', '&gt;')
            return f'<pre><code class="{lang}">{code}</code></pre>'
        
        html = re.sub(r'```(\w*)\n(.*?)```', replace_code_block, html, flags=re.DOTALL)
        
        # 转换行内代码
        html = re.sub(r'`([^`]+)`', r'<code>\1</code>', html)
        
        # 转换标题
        html = re.sub(r'^###### (.+)$', r'<h6>\1</h6>', html, flags=re.MULTILINE)
        html = re.sub(r'^##### (.+)$', r'<h5>\1</h5>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.+)$', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        
        # 转换粗体和斜体
        html = re.sub(r'\*\*\*(.+?)\*\*\*', r'<strong><em>\1</em></strong>', html)
        html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'(?<!\*)\*([^\*]+)\*(?!\*)', r'<em>\1</em>', html)
        
        # 转换链接
        html = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2">\1</a>', html)
        
        # 转换水平线 (在列表之前处理)
        html = re.sub(r'^---+$', r'<hr>', html, flags=re.MULTILINE)
        html = re.sub(r'^\*\*\*+$', r'<hr>', html, flags=re.MULTILINE)
        
        # 转换引用
        html = re.sub(r'^> (.+)$', r'<blockquote>\1</blockquote>', html, flags=re.MULTILINE)
        
        # 转换表格
        def convert_table(match):
            table_text = match.group(0)
            rows = table_text.strip().split('\n')
            if len(rows) < 2:
                return table_text
            
            html_table = '<table>'
            for i, row in enumerate(rows):
                if re.match(r'^[\|\s\-:]+$', row):
                    continue  # Skip separator row
                cells = [c.strip() for c in row.split('|') if c.strip()]
                if not cells:
                    continue
                if i == 0:
                    html_table += '<tr>' + ''.join(f'<th>{c}</th>' for c in cells) + '</tr>'
                else:
                    html_table += '<tr>' + ''.join(f'<td>{c}</td>' for c in cells) + '</tr>'
            html_table += '</table>'
            return html_table
        
        html = re.sub(r'(\|[^\n]+\|\n)+', convert_table, html)
        
        # 转换列表 - 改进版本
        lines = html.split('\n')
        result_lines = []
        in_ul = False
        in_ol = False
        
        for line in lines:
            stripped = line.strip()
            
            # 无序列表
            ul_match = re.match(r'^[\*\-\+]\s+(.+)$', stripped)
            # 有序列表
            ol_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
            
            if ul_match:
                if not in_ul:
                    if in_ol:
                        result_lines.append('</ol>')
                        in_ol = False
                    result_lines.append('<ul>')
                    in_ul = True
                result_lines.append(f'<li>{ul_match.group(1)}</li>')
            elif ol_match:
                if not in_ol:
                    if in_ul:
                        result_lines.append('</ul>')
                        in_ul = False
                    result_lines.append('<ol>')
                    in_ol = True
                result_lines.append(f'<li>{ol_match.group(2)}</li>')
            else:
                if in_ul:
                    result_lines.append('</ul>')
                    in_ul = False
                if in_ol:
                    result_lines.append('</ol>')
                    in_ol = False
                result_lines.append(line)
        
        if in_ul:
            result_lines.append('</ul>')
        if in_ol:
            result_lines.append('</ol>')
        
        html = '\n'.join(result_lines)
        
        # 处理段落 - 只在双换行处创建段落，不要把所有换行变成<br>
        # 先保护已有的HTML标签
        html = re.sub(r'\n\n+', '\n<p></p>\n', html)
        
        # 移除HTML标签之间的多余换行
        html = re.sub(r'>\s*\n\s*<', '><', html)
        
        # 非HTML标签行之间的单个换行变成空格或保留
        # 但不要在block元素前后加<br>
        block_tags = r'(?:h[1-6]|p|div|ul|ol|li|pre|table|tr|th|td|blockquote|hr)'
        html = re.sub(rf'(</{block_tags}>)\n', r'\1', html)
        html = re.sub(rf'\n(<{block_tags})', r'\1', html)
        
        # 包装完整HTML
        full_html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">{css}</head>
<body>{html}</body></html>"""
        
        return full_html
