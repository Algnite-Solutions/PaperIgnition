import paper_pull
#from backend.index_service import index_papers
import requests
import os
from backend.app.db_utils import load_config as load_backend_config
from AIgnite.data.docset import DocSetList, DocSet
import httpx
import sys
import asyncio
import yaml
from pathlib import Path

def load_config():
    """Load configuration from config.yaml file"""
    config_path = Path(__file__).parent / "config.yaml"
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def check_connection_health(api_url, timeout=None):
    if timeout is None:
        config = load_config()
        timeout = config['timeouts']['health_check']
    try:
        config = load_config()
        health_endpoint = config['api']['index']['endpoints']['health']
        response = httpx.get(f"{api_url}{health_endpoint}", timeout=timeout)
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

def index_papers_via_api(papers, api_url, store_images=False, keep_temp_image=False):
    """
    Index papers using the /index_papers/ endpoint.
    
    Args:
        papers: List of DocSet objects
        api_url: API base URL
        store_images: Whether to store images to MinIO (default: False)
        keep_temp_image: If False, delete temporary image files after successful storage (default: False)
    """
    docset_list = DocSetList(docsets=papers)
    
    # 按照IndexPapersRequest模型构建请求体
    request_data = {
        "docsets": docset_list.dict(),
        "store_images": store_images,
        "keep_temp_image": keep_temp_image
    }
    
    try:
        config = load_config()
        index_endpoint = config['api']['index']['endpoints']['index_papers']
        timeout = config['timeouts']['index_papers']
        response = httpx.post(f"{api_url}{index_endpoint}", json=request_data, timeout=timeout)
        response.raise_for_status()
        print("Indexing response:", response.json())
    except Exception as e:
        print("Failed to index papers:", e)

def search_papers_via_api(api_url, query, search_strategy=None, similarity_cutoff=None, filters=None):
    config = load_config()
    if search_strategy is None:
        search_strategy = config['generation']['search']['default_strategy']
    if similarity_cutoff is None:
        similarity_cutoff = config['generation']['search']['default_similarity_cutoff']
    """Search papers using the /find_similar/ endpoint for a single query.
    Returns a list of DocSet objects corresponding to the results.
    """
    # 检查连接健康状态
    health = check_connection_health(api_url)
    if not health:
        print(f"❌ 搜索服务 {api_url} 不可用，跳过查询 '{query}'")
        return []
    
    # 根据新的API结构构建payload
    search_config = config['generation']['search']
    payload = {
        "query": query,
        "top_k": search_config['default_top_k'],
        "similarity_cutoff": similarity_cutoff,
        "search_strategies": [(search_strategy, search_config['default_threshold'])],  # 新API使用元组格式 (strategy, threshold)
        "filters": filters,
        "result_include_types": search_config['result_include_types']  # 使用正确的结果类型
    }
    try:
        find_similar_endpoint = config['api']['index']['endpoints']['find_similar']
        timeout = config['timeouts']['search_query']
        response = httpx.post(f"{api_url}{find_similar_endpoint}", json=payload, timeout=timeout)
        response.raise_for_status()
        results = response.json()
        print(f"\nResults for query '{query}' (strategy: {search_strategy}, cutoff: {similarity_cutoff}):")
        docsets = []
        for r in results:
            # Create DocSet instance (handle missing fields gracefully)
            try:
                # 提取metadata中的信息
                metadata = r.get('metadata', {})
                
                # 处理chunks数据，确保符合DocSet定义
                def process_text_chunks(chunks_data):
                    """处理text_chunks数据，转换为符合DocSet定义的格式"""
                    if not chunks_data:
                        return []
                    
                    processed_chunks = []
                    for chunk in chunks_data:
                        if isinstance(chunk, dict):
                            # 检查是否已经是正确的格式
                            if 'id' in chunk and 'type' in chunk and 'text' in chunk:
                                processed_chunks.append(chunk)
                            elif 'chunk_id' in chunk and 'text_content' in chunk:
                                # 转换API格式到DocSet格式
                                converted_chunk = {
                                    'id': chunk['chunk_id'],
                                    'type': 'text',
                                    'text': chunk['text_content']
                                }
                                processed_chunks.append(converted_chunk)
                            else:
                                # 跳过无效的chunk
                                print(f"Warning: Skipping invalid text chunk: {chunk}")
                        else:
                            print(f"Warning: Skipping non-dict text chunk: {chunk}")
                    return processed_chunks
                
                # 为缺失的必需字段提供默认值，确保符合DocSet定义
                docset_data = {
                    'doc_id': r.get('doc_id'),
                    'title': metadata.get('title', 'Unknown Title'),
                    'authors': metadata.get('authors', []),
                    'categories': metadata.get('categories', []),
                    'published_date': metadata.get('published_date', ''),
                    'abstract': metadata.get('abstract', ''),
                    'pdf_path': metadata.get('pdf_path', ''),
                    'HTML_path': metadata.get('HTML_path'),
                    'text_chunks': process_text_chunks(r.get('text_chunks', [])),
                    'figure_chunks': [],
                    'table_chunks': [],
                    'metadata': metadata,
                    'comments': metadata.get('comments', '')
                }
                
                docset = DocSet(**docset_data)
                print(f"[DocSet] Created with title: {docset.title}")
                docsets.append(docset)
            except Exception as e:
                print(f"Failed to create DocSet for {r.get('doc_id')}: {e}")
                continue
        return docsets
    except httpx.TimeoutException:
        print(f"❌ 搜索查询 '{query}' 超时（30秒），请检查网络连接或服务器状态")
        return []
    except httpx.ConnectError:
        print(f"❌ 无法连接到搜索服务 {api_url}，请检查服务是否运行")
        return []
    except httpx.HTTPStatusError as e:
        print(f"❌ 搜索查询 '{query}' 返回错误状态码: {e.response.status_code}")
        print(f"错误详情: {e.response.text}")
        return []
    except Exception as e:
        print(f"❌ 搜索查询 '{query}' 时发生未知错误: {e}")
        return []

def save_recommendations(username, papers, api_url):
    for paper in papers:
        print(paper)
        data = {
            "paper_id": paper.get("paper_id"),
            "title": paper.get("title", ""),
            "authors": paper.get("authors", ""),
            "abstract": paper.get("abstract", ""),
            "url": paper.get("url", ""),
            "content": paper.get("content", ""),  # 必须补全
            "blog": paper.get("blog", ""),
            "recommendation_reason": paper.get("recommendation_reason", ""),
            "relevance_score": paper.get("relevance_score", None),
            "blog_abs": paper.get("blog_abs", ""),
            "blog_title": paper.get("blog_title", ""),
            "submitted": paper.get("submitted", ""),
            "comment": paper.get("comment", ""),
        }
        try:
            config = load_config()
            recommend_endpoint = config['api']['backend']['endpoints']['papers_recommend']
            timeout = config['timeouts']['save_recommendation']
            resp = httpx.post(
                f"{api_url}{recommend_endpoint}",
                params={"username": username},
                json=data,
                timeout=timeout
            )
            if resp.status_code == 201:
                print(f"✅ 推荐写入成功: {paper.get('paper_id')}")
            else:
                print(f"❌ 推荐写入失败: {paper.get('paper_id')}，原因: {resp.text}")
        except Exception as e:
            print(f"❌ 推荐写入异常: {paper.get('paper_id')}，错误: {e}")

def fetch_daily_papers(index_api_url: str, config):
    """
    Fetch daily papers and return a list of DocSet objects.
    This function is a placeholder and should be replaced with the actual implementation.
    """
    # 1. Check connection health before indexing
    health = check_connection_health(index_api_url)
    if health == "not_ready" or not health:
        print("Attempting to initialize index service...")
        # Re-check health after initialization
        if not check_connection_health(index_api_url):
            print("Exiting due to failed health check after initialization.")
            sys.exit(1)

    papers = _fetch_daily_papers()
    #papers=_dummy_paper_fetch("./orchestrator/jsons")
    print(f"Fetched {len(papers)} papers.")

    # 2. Index papers
    config = load_config()
    index_config = config['index']
    index_papers_via_api(papers, index_api_url, 
                        store_images=index_config['store_images'], 
                        keep_temp_image=index_config['keep_temp_image'])
    
    # 3. Return the papers for further processing
    return papers

import requests
from AIgnite.generation.generator import GeminiBlogGenerator, AsyncvLLMGenerator
from AIgnite.data.docset import DocSet
import os
import json
import yaml
import asyncio
#from backend.index_service import index_papers, find_similar
#from backend.user_service import get_all_users, get_user_interest

# @ch, replace it with backend.user_service
"""
to do:
以下两个接口缺少一个安全验证机制
"""
def get_all_users():
    """
        获取所有用户信息（username 和 interests_description）,返回json，示例如下
        [
            {
                'username': '3220102841@zju.edu.cn', 
                'interests_description': ['大型语言模型', '图神经网络']
            },
            {
                'username': 'chtest@qq.com', 
                'interests_description': ['大型语言模型', '图神经网络']
            }
        ]
    """
    config = load_config()
    backend_url = config['api']['backend']['base_url']
    users_endpoint = config['api']['backend']['endpoints']['users_all']
    response = requests.get(f"{backend_url}{users_endpoint}")
    response.raise_for_status()  # Raises an exception for bad status codes
    users_data = response.json()
    
    # Transform the data to the desired format
    transformed_users = []
    for user in users_data:
        transformed_users.append({
            "username": user.get("username"),
            "interests_description": user.get("interests_description", [])
        })
    return transformed_users

def get_user_interest(username: str):
    """
        获取指定用户的研究兴趣（interests_description）,返回json，示例如下
        ['大型语言模型', '图神经网络']
    """
    # 实际上username和user_email保持一致
    config = load_config()
    backend_url = config['api']['backend']['base_url']
    user_endpoint = config['api']['backend']['endpoints']['users_by_email']
    response = requests.get(f"{backend_url}{user_endpoint}/{username}") 
    response.raise_for_status() # Raises an exception for bad status codes (e.g., 404)
    user_data = response.json()
    return user_data.get("interests_description", [])


def run_Gemini_blog_generation(papers):
    config = load_config()
    paths = config['paths']
    generator = GeminiBlogGenerator(
        data_path=paths['orchestrator']['imgs'], 
        output_path=paths['output']['gemini_blogs'])
    blog = generator.generate_digest(papers)



async def run_batch_generation(papers):
    config = load_config()
    llm_config = config['api']['llm']
    paths = config['paths']
    generator = AsyncvLLMGenerator(
        model_name=llm_config['model_name'], 
        api_base=llm_config['base_url'],
        data_path=paths['orchestrator']['imgs'], 
        output_path=paths['output']['generated_blogs'])
    
    config_path = os.path.join(os.path.dirname(__file__), config['paths']['orchestrator']['config'], "prompt.yaml")
    with open(config_path, "r") as f:
        prompt_config = yaml.safe_load(f)

    system_prompt = prompt_config['prompts']['blog_generation']['system_prompt']
    user_prompt_template = prompt_config['prompts']['blog_generation']['user_prompt_template']

    prompts = []
    for paper in papers:
        # 准备图片路径
        image_path = generator.data_path
        
        prompt = user_prompt_template.format(
            title=paper.title, 
            authors=paper.authors, 
            abstract=paper.abstract, 
            text_chunks=paper.text_chunks,
            image_path=image_path,
            arxiv_id=paper.doc_id,
            table_chunks=paper.table_chunks,
        )
        text_chunk_limit = config['generation']['text_chunk_limit']
        if len(paper.text_chunks) > text_chunk_limit:
            prompt = prompt[:text_chunk_limit]
        prompts.append(prompt)
    try:
        max_tokens = config['generation']['max_tokens']
        blog = await generator.batch_generate(prompts=prompts, system_prompts=system_prompt, max_tokens=max_tokens, papers=papers)
        return blog
    except Exception as e:
        print(f"Error: {e}")
        return None

async def run_batch_generation_abs(papers):
    config = load_config()
    llm_config = config['api']['llm']
    paths = config['paths']
    generator = AsyncvLLMGenerator(
        model_name=llm_config['model_name'], 
        api_base=llm_config['base_url'],
        data_path=paths['orchestrator']['imgs'], 
        output_path=paths['output']['generated_blogs'])
    
    config_path = os.path.join(os.path.dirname(__file__), config['paths']['orchestrator']['config'], "prompt.yaml")
    with open(config_path, "r") as f:
        prompt_config = yaml.safe_load(f)

    system_prompt = prompt_config['prompts']['blog_generation_abs']['system_prompt']
    user_prompt_template = prompt_config['prompts']['blog_generation_abs']['user_prompt_template']

    prompts = []
    for paper in papers:  # 遍历 papers 而不是 blogs
        try:
            # 从磁盘读取博客文件
            blog_file_path = os.path.join(paths['output']['generated_blogs'], f"{paper.doc_id}.md")
            with open(blog_file_path, encoding="utf-8") as file:
                blog_content = file.read()
        except FileNotFoundError:
            print(f"❌ Blog file not found for {paper.doc_id}")
            continue
        
        prompt = user_prompt_template.format(
            blog=blog_content
        )
        prompts.append(prompt)
    
    try:
        max_tokens = config['generation']['max_tokens']
        abs = await generator.batch_generate_not_save(prompts=prompts, system_prompts=system_prompt, max_tokens=max_tokens, papers=papers)
        return abs
    except Exception as e:
        print(f"Error: {e}")
        return None


async def run_batch_generation_title(papers):
    config = load_config()
    llm_config = config['api']['llm']
    paths = config['paths']
    generator = AsyncvLLMGenerator(
        model_name=llm_config['model_name'], 
        api_base=llm_config['base_url'],
        data_path=paths['orchestrator']['imgs'], 
        output_path=paths['output']['generated_blogs'])
    
    config_path = os.path.join(os.path.dirname(__file__), config['paths']['orchestrator']['config'], "prompt.yaml")
    with open(config_path, "r") as f:
        prompt_config = yaml.safe_load(f)

    system_prompt = prompt_config['prompts']['blog_generation_title']['system_prompt']
    user_prompt_template = prompt_config['prompts']['blog_generation_title']['user_prompt_template']

    prompts = []
    for paper in papers:  # 遍历 papers 而不是 blogs
        prompt = user_prompt_template.format(
            title=paper.title
        )
        prompts.append(prompt)
    
    try:
        max_tokens = config['generation']['max_tokens']
        titles = await generator.batch_generate_not_save(prompts=prompts, system_prompts=system_prompt, max_tokens=max_tokens, papers=papers)
        return titles
    except Exception as e:
        print(f"Error: {e}")
        return None

from AIgnite.data.docset import *
from AIgnite.data.htmlparser import *
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import ProcessPoolExecutor, as_completed  
import json
from pathlib import Path
import os
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

def _fetch_daily_papers(time=None) -> list[DocSet]:
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

    time_slots = divide_a_day_into(time, 3)
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

def _dummy_paper_fetch(file_path: str) -> list[DocSet]:
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
    extractor.pdf_parser_helper.docs = extractor.docs
    extractor.pdf_parser_helper.remain_docparser()
    extractor.docs = extractor.pdf_parser_helper.docs
    
    # 记录新抓取的论文ID
    newly_fetched_ids = [doc.doc_id for doc in extractor.docs]
    
    extractor.serialize_docs()
    
    return newly_fetched_ids



def get_time_str(location = "Asia/Shanghai", count_delay = 1):
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