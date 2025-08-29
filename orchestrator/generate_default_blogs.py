import sys
import os
import asyncio
sys.path.append(os.path.dirname(__file__))
import utils
import paper_pull
from generate_blog import run_batch_generation
#from backend.index_service import index_papers
import requests
import os
from backend.app.db_utils import load_config as load_backend_config
from AIgnite.data.docset import DocSetList, DocSet
import httpx
import sys
import yaml

def main():
    config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/app_config.yaml")
    config = load_backend_config(config_path)
    index_api_url = config['INDEX_SERVICE']["host"]
    backend_api_url = config['APP_SERVICE']["host"]
    print("backend：",backend_api_url)
    print("index：",index_api_url)


    #print("Starting daily paper fetch...")
    papers = utils.fetch_daily_papers(index_api_url, config)
    #print("Daily paper fetch complete.")

    print("Starting blog generation for existing users...")
    asyncio.run(utils.blog_generation_for_storage(index_api_url, backend_api_url, papers))
    print("Blog generation for existing users complete.")
    
if __name__ == "__main__":
    main()