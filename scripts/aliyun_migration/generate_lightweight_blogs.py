import os
import sys
import yaml
import asyncio
import time
import aiohttp
from tqdm import tqdm
from pathlib import Path

# Add AIgnite/src to Python path so we can import from it
aignite_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "AIgnite", "src"))
sys.path.insert(0, aignite_path)

print("🚀 Script initializing...", flush=True)

import psycopg2
from google import genai
from google.genai import types

from AIgnite.generation.generator import GeminiBlogGenerator_default, _load_prompt_config
from AIgnite.data.docset import DocSet
from AIgnite.recommendation.LLMReranker import extract_first_page_pdf

# We monkey-patch the prompt loader to force English prompt
original_load_prompt_config = _load_prompt_config

def forced_en_prompt_loader(input_format="pdf"):
    config = original_load_prompt_config(input_format)
    if "blog_generation_prompt_en" in config:
        config["blog_generation_prompt"] = config["blog_generation_prompt_en"]
    return config

import AIgnite.generation.generator
AIgnite.generation.generator._load_prompt_config = forced_en_prompt_loader

# Configuration
DB_URL_TEST = os.getenv("METADATA_DB_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not DB_URL_TEST or not GEMINI_API_KEY:
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env.app")
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            for line in f:
                line = line.strip()
                if not DB_URL_TEST and (line.startswith("export METADATA_DB_URL=") or line.startswith("METADATA_DB_URL=")):
                    DB_URL_TEST = line.split("=", 1)[1].strip('"\'')
                if not GEMINI_API_KEY and (line.startswith("export GEMINI_API_KEY=") or line.startswith("GEMINI_API_KEY=")):
                    GEMINI_API_KEY = line.split("=", 1)[1].strip('"\'')

if not DB_URL_TEST:
    print("Error: METADATA_DB_URL not found in environment or .env.app")
    sys.exit(1)

if not GEMINI_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment or .env.app, make sure to export it.")

MODEL_ID = "gemini-3.1-flash-lite-preview"
MAX_CONCURRENT_TASKS = 50   # Increased from 20 - both download and Gemini are I/O bound
TOTAL_LIMIT = 50000         # Safety limit for total papers to fetch in one run
DOWNLOAD_TIMEOUT = 30       # Seconds before giving up on a PDF download

pricing_input = 0.25 / 1_000_000
pricing_output = 1.5 / 1_000_000

def get_db_connection(max_retries=3):
    for attempt in range(1, max_retries + 1):
        try:
            return psycopg2.connect(DB_URL_TEST)
        except psycopg2.OperationalError as e:
            if attempt < max_retries:
                wait_time = 2 ** attempt
                print(f"⚠️ Database connection failed (attempt {attempt}/{max_retries}): {e}. Retrying in {wait_time}s...", flush=True)
                time.sleep(wait_time)
            else:
                raise

async def download_pdf_async(session, arxiv_id, output_path):
    """Truly async PDF download using aiohttp."""
    url = f"https://arxiv.org/pdf/{arxiv_id}.pdf"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=DOWNLOAD_TIMEOUT)) as response:
            if response.status == 200:
                with open(output_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                return True
            print(f"[{arxiv_id}] Arxiv returned status {response.status}", flush=True)
    except asyncio.TimeoutError:
        print(f"[{arxiv_id}] Download timed out ({DOWNLOAD_TIMEOUT}s)", flush=True)
    except Exception as e:
        print(f"[{arxiv_id}] Download error: {e}", flush=True)
    return False

def update_db(doc_id, blog_content):
    try:
        conn = get_db_connection()
    except Exception as e:
        print(f"❌ Could not establish database connection for {doc_id}: {e}", flush=True)
        return

    cur = conn.cursor()
    try:
        cur.execute("UPDATE papers SET blog = %s WHERE doc_id = %s", (blog_content, doc_id))
        conn.commit()
        print(f"✅ Saved generated blog for {doc_id} to database.", flush=True)
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to save blog for {doc_id} to database: {e}", flush=True)
    finally:
        cur.close()
        conn.close()

async def check_affiliation(client, first_page_bytes, arxiv_id):
    prompt = """
    Evaluate the provided first page of a research paper. 
    1. Identify the authors' affiliations.
    2. Answer YES if any author is affiliated with a top-tier university (e.g., MIT, Stanford, Berkeley, Tsinghua, Oxford, Cambridge) or a major tech company (e.g., Google, Meta, Microsoft, Apple, OpenAI, Amazon, DeepMind, Anthropic). 
    3. Answer NO otherwise.
    
    Output exactly YES or NO and nothing else.
    """
    
    try:
        response = await client.aio.models.generate_content(
            model=MODEL_ID,
            contents=[
                prompt,
                types.Part.from_bytes(data=first_page_bytes, mime_type='application/pdf')
            ]
        )
        
        input_tokens = response.usage_metadata.prompt_token_count
        output_tokens = response.usage_metadata.candidates_token_count
        cost = (input_tokens * pricing_input) + (output_tokens * pricing_output)

        answer = response.text.strip().upper()
        if "YES" in answer:
            return True, input_tokens, output_tokens, cost
        return False, input_tokens, output_tokens, cost
    except Exception as e:
        print(f"[{arxiv_id}] Affiliation check error: {e}", flush=True)
        return False, 0, 0, 0

async def generate_blog_full(generator, paper_docset):
    start_time = time.time()
    
    loop = asyncio.get_event_loop()
    
    def sync_generate():
        try:
            generator._generate_single_blog(paper_docset, input_format="pdf")
            md_path = os.path.join(generator.output_path, f"{paper_docset.doc_id}.md")
            if os.path.exists(md_path):
                with open(md_path, "r", encoding="utf-8") as f:
                    return f.read()
            return None
        except Exception as e:
             print(f"[{paper_docset.doc_id}] Generation error: {e}", flush=True)
             return None

    blog_content = await loop.run_in_executor(None, sync_generate)
    
    if blog_content:
        update_db(paper_docset.doc_id, blog_content)
    
    elapsed = time.time() - start_time
    print(f"[{paper_docset.doc_id}] Full generation took {elapsed:.1f}s", flush=True)
    return blog_content

async def process_paper(client, generator, doc_id, title, semaphore, http_session, pbar):
    async with semaphore:
        try:
            pdf_path = f"/tmp/{doc_id}.pdf"
            if not os.path.exists(pdf_path):
                success = await download_pdf_async(http_session, doc_id, pdf_path)
                if not success:
                    pbar.update(1)
                    return {"status": "error", "doc_id": doc_id, "error": "Download failed"}

            first_page_bytes = extract_first_page_pdf(pdf_path)
            if not first_page_bytes:
                pbar.update(1)
                return {"status": "error", "doc_id": doc_id, "error": "First page extraction failed"}

            is_top_institution, in_tok, out_tok, cost = await check_affiliation(client, first_page_bytes, doc_id)
            
            if is_top_institution:
                paper_docset = DocSet(
                    doc_id=doc_id,
                    title=title,
                    abstract="",
                    authors=[],
                    categories=[],
                    published_date="",
                    pdf_path=pdf_path,
                    HTML_path="",
                    text_chunks=[],
                    table_chunks=[],
                    figure_chunks=[]
                )
                await generate_blog_full(generator, paper_docset)
                pbar.update(1)
                return {
                    "status": "generated",
                    "doc_id": doc_id,
                    "filter_in_tok": in_tok,
                    "filter_out_tok": out_tok,
                    "filter_cost": cost
                }
            else:
                pbar.update(1)
                return {
                    "status": "skipped",
                    "doc_id": doc_id,
                    "filter_in_tok": in_tok,
                    "filter_out_tok": out_tok,
                    "filter_cost": cost
                }
        except Exception as e:
            print(f"[{doc_id}] Unexpected error: {e}", flush=True)
            pbar.update(1)
            return {"status": "error", "doc_id": doc_id, "error": str(e)}

async def main_async():
    print("Connecting to database...", flush=True)
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("SELECT doc_id, title FROM papers WHERE blog IS NULL ORDER BY published_date DESC LIMIT %s", (TOTAL_LIMIT,))
    papers = cur.fetchall()
    
    cur.close()
    conn.close()

    if not papers:
        print("No papers found that need a blog.")
        return

    print(f"Found {len(papers)} papers to process.", flush=True)
    print(f"Concurrency: {MAX_CONCURRENT_TASKS} | Download timeout: {DOWNLOAD_TIMEOUT}s", flush=True)

    if not GEMINI_API_KEY:
        print("Error: GEMINI_API_KEY is not set. Please export it before running.")
        sys.exit(1)

    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Use a shared aiohttp session for all downloads (connection pooling)
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT_TASKS)
    async with aiohttp.ClientSession(connector=connector) as http_session:
        try:
            blog_dir = "/tmp/blogs"
            os.makedirs(blog_dir, exist_ok=True)
            
            generator = GeminiBlogGenerator_default(
                model_name=MODEL_ID,
                data_path="http://oss.paperignition.com/imgs",
                output_path=blog_dir,
                input_format="pdf"
            )

            total_start_time = time.time()
            semaphore = asyncio.Semaphore(MAX_CONCURRENT_TASKS)
            
            pbar = tqdm(total=len(papers), desc="Processing Papers", unit="paper")
            
            tasks = []
            for doc_id, title in papers:
                tasks.append(process_paper(client, generator, doc_id, title, semaphore, http_session, pbar))

            results = await asyncio.gather(*tasks, return_exceptions=True)
            pbar.close()

            total_filter_cost = 0.0
            total_filter_in = 0
            total_filter_out = 0
            generated_count = 0
            skipped_count = 0
            error_count = 0

            for res in results:
                if isinstance(res, Exception):
                    error_count += 1
                    continue
                if res:
                    total_filter_cost += res.get("filter_cost", 0)
                    total_filter_in += res.get("filter_in_tok", 0)
                    total_filter_out += res.get("filter_out_tok", 0)
                    if res["status"] == "generated":
                        generated_count += 1
                    elif res["status"] == "skipped":
                        skipped_count += 1
                    else:
                        error_count += 1

            total_duration = time.time() - total_start_time

            print("\n" + "="*50, flush=True)
            print("Batch Processing Summary", flush=True)
            print("="*50, flush=True)
            print(f"Total Papers Processed: {len(papers)}", flush=True)
            print(f"Generated Blogs: {generated_count}", flush=True)
            print(f"Skipped Papers: {skipped_count}", flush=True)
            print(f"Failed Papers: {error_count}", flush=True)
            print(f"Total Batch Time: {total_duration:.2f} seconds ({total_duration/3600:.1f} hours)", flush=True)
            print(f"Total Step 1 (Affiliation Filter) Input Tokens: {total_filter_in:,}", flush=True)
            print(f"Total Step 1 (Affiliation Filter) Output Tokens: {total_filter_out:,}", flush=True)
            print(f"Total Step 1 (Affiliation Filter) Cost: ${total_filter_cost:.6f}", flush=True)
            print("Step 2 (Full Generation) tokens/costs are printed inline by AIgnite generator.", flush=True)
            print("="*50, flush=True)
        finally:
            client.close()

def main():
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
