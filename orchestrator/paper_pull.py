from AIgnite.data.docset import *
from AIgnite.data.htmlparser import *
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed  
import json
from pathlib import Path
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def fetch_daily_papers(time=None) -> list[DocSet]:
    # Replace this with your actual fetcher
    if time is None:
        time = get_time_str()
    print(f"fetching papers for {time}")
    docs = []
    # set up
    base_dir = os.path.dirname(__file__)
    html_text_folder = os.path.join(base_dir, "htmls")
    pdf_folder_path = os.path.join(base_dir, "pdfs")
    image_folder_path = os.path.join(base_dir, "imgs")
    json_output_path = os.path.join(base_dir, "jsons")
    arxiv_pool_path = os.path.join(base_dir, "html_url_storage/html_urls.txt")

    time_slots = divide_a_day_into(time, 1)
    # time_slots = divide_a_day_into('202405300000', 3)
    
    #make sure the folders exist
    os.makedirs(os.path.dirname(arxiv_pool_path), exist_ok=True)
    Path(arxiv_pool_path).touch(exist_ok=True)
    for path in [html_text_folder, pdf_folder_path, image_folder_path, json_output_path]:
        os.makedirs(path, exist_ok=True)

    #fetch daily papers in parallel
    newly_fetched_ids = set()
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = []
        for i in range(len(time_slots) - 1):
            start_str = time_slots[i]
            end_str = time_slots[i + 1]
            futures.append(executor.submit(run_extractor_for_timeslot, start_str, end_str))

        for f in futures:
            result = f.result()
            if result:  # 如果返回了新抓取的ID列表
                newly_fetched_ids.update(result)
    
    print(f"📊 新抓取论文ID数量: {len(newly_fetched_ids)}")
    #summary docs from json - only return newly fetched papers
    new_docs = []
    for json_file in Path(json_output_path).glob("*.json"):
        # 检查文件名是否包含新抓取的arxiv ID
        file_name = json_file.stem  # 去掉.json扩展名
        if file_name in newly_fetched_ids:
            with open(json_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                try:
                    docset = DocSet(**data)
                    new_docs.append(docset)
                    print(f"✅ 新抓取论文: {docset.doc_id} - {docset.title}")
                except Exception as e:
                    print(f"Failed to parse {json_file.name}: {e}")
    
    print(f"📊 新抓取论文数量: {len(new_docs)}")
    
    return new_docs

def dummy_paper_fetch(file_path: str) -> list[DocSet]:
    docs = []
    path_obj = Path(file_path)
    
    if path_obj.is_dir():
        i = 0
        for json_file in path_obj.glob("*.json"):
            with open(json_file, "r", encoding="utf-8") as f:
                try:
                    data = json.load(f)
                    docset = DocSet(**data)
                    print(f"Parsed {json_file.name}")
                    docs.append(docset)
                except Exception as e:
                    print(f"Failed to parse {json_file.name}: {e}")
    else:
        print(f"The path {file_path} is not a directory")
    return docs

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

    # TODO: rongcan: a separater pdf_extractor instead of this fall back logic below
    
    #extractor.pdf_parser_helper.docs = extractor.docs
    #extractor.pdf_parser_helper.remain_docparser()
    #extractor.docs = extractor.pdf_parser_helper.docs
    
    # 记录新抓取的论文ID
    newly_fetched_ids = [doc.doc_id for doc in extractor.docs]
    
    extractor.serialize_docs()
    
    return newly_fetched_ids



def get_time_str(location = "Asia/Shanghai", count_delay = 2):
    # 设定本地时区（可根据需要修改）
    local_tz = ZoneInfo(location)  # 例如上海
    # 获取本地当前时间，精确到分钟
    local_now = (datetime.now(local_tz)-timedelta(days=count_delay)).replace(second=0, microsecond=0)
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
