import requests
import os
import csv
import time
from bs4 import BeautifulSoup

def scrape_bcp_rfcs():
    """使用BeautifulSoup抓取Best Current Practice RFCs"""
    url = "https://www.rfc-editor.org/search/rfc_search_detail.php?sortkey=Number&sorting=DESC&page=All&pubstatus%5B%5D=Best%20Current%20Practice"
    
    try:
        # 发送请求获取页面
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
        }
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        # 使用BeautifulSoup解析HTML
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # 保存格式化HTML以便检查
        with open('rfc_page.html', 'w', encoding='utf-8') as f:
            f.write(soup.prettify())
        print("已保存格式化HTML到rfc_page.html文件")
        
        # 查找表格 - 尝试基于class查找，如果没有则获取第一个表格
        table = soup.find('table', class_='gridtable')
        if not table:
            tables = soup.find_all('table')
            if tables:
                table = tables[0]
                print("未找到gridtable类表格，使用第一个表格")
            else:
                print("页面中未找到任何表格")
                return []
        
        # 获取所有表格行
        rows = table.find_all('tr')
        print(f"找到表格，包含 {len(rows)} 行")
        
        if not rows:
            print("表格中没有行数据")
            return []
            
        # 检查表头
        header_row = rows[0]
        headers = [th.text.strip() for th in header_row.find_all(['th', 'td'])]
        print(f"表头: {headers}")
        
        bcp_rfcs = []
        
        # 处理数据行 (跳过表头)
        for row in rows[1:]:
            try:
                cells = row.find_all('td')
                
                if len(cells) < 5:
                    continue
                
                # 获取RFC编号
                # 获取RFC编号
                rfc_cell = cells[0]
                rfc_link = rfc_cell.find('a')  # 查找链接
                if rfc_link:
                    rfc_num = rfc_link.text.strip().replace('RFC', '').strip()
                else:
                    print(f"警告: 无法提取RFC编号: {rfc_cell}")
                    continue
                
                # 获取下载链接
                downloadtype = cells[1].text.strip()
                print(f"文档格式：\t{downloadtype}")

                # 获取标题
                title = cells[2].text
                print(f"标题：\t{title}")

                # 获取日期
                date = cells[4].text
                print(f"日期：\t{date}")
                
                # 获取状态信息
                status_cell = cells[6]
                status_text = status_cell.text.strip()
                print(f"状态：\t{status_text}")
                
                
                # 获取所有可用链接
                rfc_links = {}
                
                # 检查RFC编号单元格中的链接
                for a_tag in cells[1].find_all('a'):
                    href = a_tag.get('href')
                    if href:
                        if href.endswith('.html'):
                            rfc_links['html'] = href
                        elif href.endswith('.txt'):
                            rfc_links['txt'] = href
                        elif href.endswith('.pdf'):
                            rfc_links['pdf'] = href
                        elif href.endswith('.xml'):
                            rfc_links['xml'] = href
                        else:
                            # 基本链接 - 通常是文档主页
                            rfc_links['main'] = href
                
                # 如果没有在RFC编号单元格找到链接，则尝试标题单元格
                if not rfc_links:
                    for a_tag in title.find_all('a'):
                        href = a_tag.get('href')
                        if href:
                            if href.endswith('.html'):
                                rfc_links['html'] = href
                            elif href.endswith('.txt'):
                                rfc_links['txt'] = href
                            elif href.endswith('.pdf'):
                                rfc_links['pdf'] = href
                            elif href.endswith('.xml'):
                                rfc_links['xml'] = href
                            else:
                                # 基本链接
                                rfc_links['main'] = href
                
                # 如果还没有找到链接，构造标准RFC URL
                if not rfc_links:
                    base_url = f"https://www.rfc-editor.org/rfc/rfc{rfc_num}"
                    rfc_links = {
                        'html': f"{base_url}.html",
                        'txt': f"{base_url}.txt",
                        'pdf': f"{base_url}.pdf",
                        'xml': f"{base_url}.xml"
                    }
                
                # 添加到结果列表
                bcp_rfcs.append({
                    'rfc_number': rfc_num,
                    'title': title,
                    'status': "Best Current Practice",
                    'links': rfc_links
                })
                
                print(f"已找到: RFC {rfc_num} (BCP {bcp_num}): {title}")
            
            except Exception as e:
                print(f"处理行时出错: {e}")
                continue
        
        return bcp_rfcs
    
    except Exception as e:
        print(f"错误: {e}")
        return []

def download_rfcs(bcp_rfcs, base_dir='rfcs'):
    """按文件类型下载RFC文档，并实时更新CSV文件状态"""
    # 创建基础目录
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    # 创建CSV文件记录元数据
    csv_path = os.path.join(base_dir, 'bcp_rfcs_metadata.csv')
    if not os.path.exists(csv_path):
        # 如果CSV文件不存在，初始化文件并写入表头
        with open(csv_path, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = ['bcp_number', 'rfc_number', 'title', 'status', 'format', 'file_path', 'downloaded']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
    
    # 遍历每个RFC
    for bcp in bcp_rfcs:
        rfc_num = bcp['rfc_number']
        bcp_num = bcp.get('bcp_number', '')
        title = bcp.get('title', '')
        status = bcp.get('status', '')
        
        for format_type, url in bcp.get('links', {}).items():
            try:
                # 按文件类型创建目录
                format_dir = os.path.join(base_dir, format_type)
                if not os.path.exists(format_dir):
                    os.makedirs(format_dir)
                
                # 构造文件名
                file_name = f"rfc{rfc_num}.{format_type}" if format_type != 'main' else f"rfc{rfc_num}_index.html"
                file_path = os.path.join(format_dir, file_name)
                
                # 检查CSV文件中是否已记录为已下载
                already_downloaded = False
                with open(csv_path, 'r', newline='', encoding='utf-8') as csvfile:
                    reader = csv.DictReader(csvfile)
                    for row in reader:
                        if row['rfc_number'] == rfc_num and row['format'] == format_type and row['downloaded'] == 'Yes':
                            already_downloaded = True
                            break
                
                if already_downloaded:
                    print(f"文件已下载，跳过: {file_path}")
                    continue
                
                # 下载文件
                print(f"正在下载 RFC {rfc_num} ({format_type}格式)...")
                response = requests.get(url)
                
                # 检查响应状态
                if response.status_code != 200:
                    print(f"  下载失败: HTTP {response.status_code}")
                    continue
                
                # 保存内容
                with open(file_path, 'wb') as f:
                    f.write(response.content)
                
                print(f"  成功保存到 {file_path}")
                
                # 更新CSV文件
                with open(csv_path, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=['bcp_number', 'rfc_number', 'title', 'status', 'format', 'file_path', 'downloaded'])
                    writer.writerow({
                        'bcp_number': bcp_num,
                        'rfc_number': rfc_num,
                        'title': title,
                        'status': status,
                        'format': format_type,
                        'file_path': file_path,
                        'downloaded': 'Yes'
                    })
                
                # 避免请求过于频繁
                time.sleep(0.5)
            
            except Exception as e:
                print(f"  下载 {format_type} 格式时出错: {e}")

def main():
    print("正在抓取Best Current Practice RFCs...")
    bcp_rfcs = scrape_bcp_rfcs()
    
    if bcp_rfcs:
        print(f"找到 {len(bcp_rfcs)} 个BCP RFC文档")
        
        # 打印前5个RFC的信息
        print("\n所有RFC文档:")
        for i, bcp in enumerate(bcp_rfcs[:]):
            bcp_num = bcp.get('bcp_number', 'N/A')
            title = bcp.get('title', 'Unknown Title')
            rfc_num = bcp.get('rfc_number', 'N/A')
            formats = list(bcp.get('links', {}).keys())
            print(f"{i+1}. RFC {rfc_num} (BCP {bcp_num}): {title}")
            print(f"   可用格式: {', '.join(formats)}")
        
        # 询问用户是否下载
        download_choice = input("\n是否下载这些RFC文档? (y/n): ")
        if download_choice.lower() == 'y':
            download_rfcs(bcp_rfcs)
            print("所有RFC文档下载完成!")
    else:
        print("未找到BCP文档。请检查网站结构或网络连接。")

if __name__ == "__main__":
    main()