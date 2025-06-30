from AIgnite.data.docset import *
from AIgnite.data.htmlparser import *
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed  
import json
from pathlib import Path
import os

def fetch_daily_papers() -> list[DocSet]:
    # Replace this with your actual fetcher
    docs = []
    # set up
    base_dir = os.path.dirname(__file__)
    html_text_folder = os.path.join(base_dir, "htmls")
    pdf_folder_path = os.path.join(base_dir, "pdfs")
    image_folder_path = os.path.join(base_dir, "imgs")
    json_output_path = os.path.join(base_dir, "jsons")
    arxiv_pool_path = os.path.join(base_dir, "html_url_storage/html_urls.txt")

    #decide date and divide time slot
    today = datetime.now(timezone.utc).date()# - timedelta(days=2)
    date_str = today.strftime("%Y%m%d")
    #time_slots = divide_one_day_into(date_str, 3)
    time_slots = divide_one_day_into('20240530', 3)
    
    #make sure the folders exist
    os.makedirs(os.path.dirname(arxiv_pool_path), exist_ok=True)
    Path(arxiv_pool_path).touch(exist_ok=True)
    for path in [html_text_folder, pdf_folder_path, image_folder_path, json_output_path]:
        os.makedirs(path, exist_ok=True)

    #fetch daily papers in parallel
    with ThreadPoolExecutor(max_workers=1) as executor:
        futures = []
        for i in range(len(time_slots) - 1):
            start_str = time_slots[i]
            end_str = time_slots[i + 1]
            futures.append(executor.submit(run_extractor_for_timeslot, start_str, end_str))

        for f in futures:
            f.result()
    
    #summary docs from json
    for json_file in Path(json_output_path).glob("*.json"):
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            try:
                docset = DocSet(**data)
                docs.append(docset)
            except Exception as e:
                print(f"Failed to parse {json_file.name}: {e}")

    return docs

def dummy_paper_fetch(file_path: str) -> list[DocSet]:
    docs = []
    path_obj = Path(file_path)
    
    if path_obj.is_dir():
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
    ak = os.getenv("VOLCENGINE_AK")
    sk = os.getenv("VOLCENGINE_SK")

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


def divide_one_day_into(date: str, count: int):
    time_sec = []
    time_last = 24 / count
    for i in range(count):
        clock = int(i * time_last)
        if clock >= 10:
            time_sec.append(date + str(clock) + "00")
        else:
            time_sec.append(date + "0" + str(clock) + "00")
    time_sec.append(date + "2359")
    return time_sec
