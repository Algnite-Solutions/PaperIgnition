import os
import sys
import yaml
import requests
import psycopg2
import time

# Add AIgnite to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../AIgnite/src')))

# Use .env.test
def read_env_file(path):
    env_vars = {}
    with open(path, 'r') as f:
        for line in f:
            line = line.strip()
            if line.startswith('export '):
                line = line[len('export '):].strip()
            if '=' in line and not line.startswith('#'):
                key, value = line.split('=', 1)
                value = value.strip().strip('"').strip("'")
                env_vars[key] = value
    return env_vars

def download_pdf(doc_id, save_path):
    url = f"https://arxiv.org/pdf/{doc_id}.pdf"
    print(f"Downloading {url}...")
    headers = {'User-Agent': 'Mozilla/5.0'}
    response = requests.get(url, headers=headers)
    response.raise_for_status()
    with open(save_path, 'wb') as f:
        f.write(response.content)

def main():
    env_path = os.path.join(os.path.dirname(__file__), '../../.env.test')
    env_vars = read_env_file(env_path)
    if 'METADATA_DB_URL' not in env_vars:
        raise ValueError("METADATA_DB_URL not found in .env.test")
        
    db_url = env_vars['METADATA_DB_URL']
    
    # Import the generator from AIgnite
    from AIgnite.generation.generator import GeminiBlogGenerator_default
    from AIgnite.data.docset import DocSet
    import AIgnite.generation.generator as generator_module
    
    # Monkey-patch _load_prompt_config to use english prompt
    original_load_prompt_config = generator_module._load_prompt_config
    
    def patched_load_prompt_config(input_format="pdf"):
        config = original_load_prompt_config(input_format)
        # Force the blog_generation_prompt to use the english version
        if 'blog_generation_prompt_en' in config:
            config['blog_generation_prompt'] = config['blog_generation_prompt_en']
        return config
        
    generator_module._load_prompt_config = patched_load_prompt_config
        
    print("Connecting to database...")
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, doc_id, title 
        FROM papers 
        WHERE blog IS NULL 
        ORDER BY id DESC 
        LIMIT 5;
    """)
    papers_rows = cursor.fetchall()
    
    if not papers_rows:
        print("No papers without blog found.")
        return
        
    print(f"Found {len(papers_rows)} papers.")
    
    pdf_dir = '/tmp/papers'
    blog_dir = '/tmp/blogs'
    os.makedirs(pdf_dir, exist_ok=True)
    os.makedirs(blog_dir, exist_ok=True)
    
    # Create DocSets
    papers_to_generate = []
    
    for paper_id, doc_id, title in papers_rows:
        print(f"\n[{doc_id}] Preparing: {title}")
        pdf_path = os.path.join(pdf_dir, f"{doc_id}.pdf")
        try:
            download_pdf(doc_id, pdf_path)
            
            # Create a mock DocSet
            paper_docset = DocSet(
                doc_id=doc_id,
                title=title,
                abstract="",
                authors=[],
                pdf_path=pdf_path,
                text_chunks=[],
                table_chunks=[],
                figure_chunks=[]
            )
            # Store ID for later update
            paper_docset._db_id = paper_id
            papers_to_generate.append(paper_docset)
        except Exception as e:
            print(f"Failed to prepare {doc_id}: {e}")

    if not papers_to_generate:
        print("No papers prepared successfully.")
        return

    # Initialize Gemini client using AIgnite class
    if "GEMINI_API_KEY" not in os.environ:
        print("WARNING: GEMINI_API_KEY not found in environment, make sure to export it.")
        
    generator = GeminiBlogGenerator_default(
        model_name="gemini-3.1-flash-lite-preview",
        data_path="http://oss.paperignition.com/imgs",
        output_path=blog_dir,
        input_format="pdf"
    )
    
    print(f"\nGenerating blogs using AIgnite.GeminiBlogGenerator_default...")
    # This will generate chunks and save to output_path in threads
    generator.generate_digest(papers_to_generate, input_format="pdf")
    
    print(f"\nGeneration complete. Reading results and updating DB...")
    
    # Write back to DB
    for paper in papers_to_generate:
        md_file = os.path.join(blog_dir, f"{paper.doc_id}.md")
        if os.path.exists(md_file):
            with open(md_file, "r", encoding="utf-8") as f:
                blog_content = f.read()
                
            cursor.execute("UPDATE papers SET blog = %s WHERE id = %s", (blog_content, paper._db_id))
            conn.commit()
            print(f"✅ Saved generated blog for {paper.doc_id} to database.")
        else:
            print(f"❌ Markdown file not found for {paper.doc_id}")
            
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
