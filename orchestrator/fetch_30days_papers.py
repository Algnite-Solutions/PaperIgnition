from AIgnite.data.docset import *
from AIgnite.data.htmlparser import *
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed  
import json
from pathlib import Path
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import paper_pull
from generate_blog import run_batch_generation
#from backend.index_service import index_papers
import requests
import os
from backend.app.db_utils import load_config as load_backend_config
from AIgnite.data.docset import DocSetList, DocSet
import httpx
import sys


def initialize_database(api_url, config):
    try:
        payload = {"config": config}
        response = httpx.post(f"{api_url}/init_database", json=payload, params={"recreate_databases": True}, timeout=60.0)
        response.raise_for_status()
        print("✅ Database and indexer initialized:", response.json())
        return True
    except Exception as e:
        print("❌ Failed to initialize database/indexer:", e)
        return False

def check_connection_health(api_url, timeout=5.0):
    try:
        response = httpx.get(f"{api_url}/health", timeout=timeout)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "healthy" and data.get("indexer_ready"):
                print("✅ Connection health check passed")
                return True
            elif data.get("status") == "healthy" and not data.get("indexer_ready"):
                print("❌ API server is not ready: ", data)
                return "not_ready"
            else:
                print("❌ API server unhealthy: ", data)
        else:
            print(f"❌ Health check failed: {response.text}")
    except Exception as e:
        print(f"❌ Error: API server not accessible at {api_url}")
        print(f"Error details: {str(e)}")
    return False

def index_papers_via_api(papers, api_url):
    docset_list = DocSetList(docsets=papers)
    data = docset_list.dict()
    try:
        response = httpx.post(f"{api_url}/index_papers/", json=data, timeout=3000.0)
        response.raise_for_status()
        print("Indexing response:", response.json())
    except Exception as e:
        print("Failed to index papers:", e)

def run_extractor_for_timeslot(start_str, end_str):
    base_dir = os.path.dirname(__file__)
    html_text_folder = os.path.join(base_dir, "htmls")
    pdf_folder_path = os.path.join(base_dir, "pdfs")
    image_folder_path = os.path.join(base_dir, "imgs")
    json_output_path = os.path.join(base_dir, "jsons")
    arxiv_pool_path = os.path.join(base_dir, "html_url_storage/html_urls.txt")
    # 从环境变量或配置文件获取密钥，避免硬编码
    ak = os.getenv("VOLCENGINE_AK", "")
    sk = os.getenv("VOLCENGINE_SK", "")

    extractor = ArxivHTMLExtractor(
        html_text_folder=html_text_folder,
        pdf_folder_path=pdf_folder_path,
        arxiv_pool=arxiv_pool_path,
        image_folder_path=image_folder_path,
        json_path=json_output_path,
        volcengine_ak=ak,
        volcengine_sk=sk,
        start_time=start_str,
        end_time=end_str
    )

    extractor.extract_all_htmls()
    extractor.pdf_parser_helper.docs = extractor.docs
    extractor.pdf_parser_helper.remain_docparser()
    extractor.docs = extractor.pdf_parser_helper.docs
    extractor.serialize_docs()

def get_time_str(location = "Asia/Shanghai"):
    # 设定本地时区（可根据需要修改）
    local_tz = ZoneInfo(location)  # 例如上海
    # 获取本地当前时间，精确到分钟
    local_now = datetime.now(local_tz).replace(second=0, microsecond=0)
    # 转换为UTC时间
    utc_now = local_now.astimezone(ZoneInfo("UTC"))
    # 转为指定格式字符串
    utc_str = utc_now.strftime("%Y%m%d%H%M")
    return utc_str

# 新增函数
def divide_a_day_into(time: str, count: int):
    """
    输入: time (如202507150856), count (如3)
    输出: 将[前一天同一时刻, 输入时刻]分成count份，返回每个分段的时间点字符串数组（精确到分钟，格式为%Y%m%d%H%M），包含头尾。
    """
    from datetime import datetime, timedelta
    fmt = "%Y%m%d%H%M"
    end_time = datetime.strptime(time, fmt)
    start_time = end_time - timedelta(days=1)
    total_minutes = int((end_time - start_time).total_seconds() // 60)
    step = total_minutes / count
    result = []
    for i in range(count + 1):
        t = start_time + timedelta(minutes=round(i * step))
        result.append(t.strftime(fmt))
    return result

def fetch_past_n_days_papers(n_days: int, index_api_url: str, config):
    """
    抓取过去n天的所有paper，并每天索引到数据库
    """

    # 检查和初始化数据库
    health = check_connection_health(index_api_url)
    if health == "not_ready" or not health:
        print("Attempting to initialize index service...")
        if not initialize_database(index_api_url, config):
            print("Exiting due to failed indexer initialization.")
            sys.exit(1)
        # Re-check health after initialization
        if not check_connection_health(index_api_url):
            print("Exiting due to failed health check after initialization.")
            sys.exit(1)
            
    today = datetime.now()
    start_day = today - timedelta(days=31)
    log_path = "/data3/guofang/peirongcan/PaperIgnition/orchestrator/dayslog.txt"
    def log_print(msg):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_msg = f"[{timestamp}] {msg}"
        print(log_msg)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(log_msg + "\n")
    for i in range(n_days):
        day = start_day - timedelta(days=i)
        # 设定为当天中午12点，保证格式为%Y%m%d%H%M
        day_time_str = day.strftime("%Y%m%d") + "1200"
        log_print(f"抓取时间: {day_time_str}")
        papers = paper_pull.fetch_daily_papers(day_time_str)
        log_print(f"{day_time_str} 抓取到 {len(papers)} 篇paper")
        if not papers:
            continue
        # 索引当天paper
        index_papers_via_api(papers, index_api_url)
        log_print(f"索引完成: {day_time_str}")

    print(f"过去{n_days}天抓取并索引完成。")

def main():
    print("开始抓取30天paper")
    config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/app_config.yaml")
    config = load_backend_config(config_path)
    index_api_url = config['INDEX_SERVICE']["host"]
    backend_api_url = config['APP_SERVICE']["host"]
    print("backend：", backend_api_url)
    print("index：", index_api_url)

    print("Starting 30 days paper fetch...")
    fetch_past_n_days_papers(30, index_api_url, config)
    print("30 days paper fetch complete.")

if __name__ == "__main__":
    main()