from AIgnite.data.docset import DocSet, DocSetList
# from AIgnite.data.docparser_new import ArxivPDFExtractor

from concurrent.futures import ProcessPoolExecutor, as_completed  
import json
from pathlib import Path
import os

def fetch_daily_papers() -> list[DocSet]:
    # Replace this with your actual fetcher
    return [
        DocSet(paper_id="001", title="Example Title", chunks=[])
        # ...
    ]



# TODO: @Prongcan delelte below two functions when you finished the arxiv_daily pull
def test_process_single_html(local_file_path: Path, output_dir: Path, pdf_path: Path):
    """
    Function to process a single HTML file.
    Args:
        local_file_path (Path): The path of the local HTML file.
        output_dir (Path): The path of the output directory for saving the extracted documents and related files.
    Returns:
        DocSet: A DocSet object containing the information extracted from the HTML file.
    """
    extractor = ArxivHTMLExtractor()
    html = extractor.load_html(local_file_path)
    docs = extractor.extract_docset(html, output_dir, pdf_path)
    extractor.serialize_docs(output_dir)
    return docs

def test_batch_process_htmls(input_dir: str, output_dir: str, pdf_path: str, max_workers: int = 9):  
    """
    Function to batch process multiple HTML files using a process pool for parallel processing.
    Args:
        input_dir (str): The path of the input directory containing HTML files.
        output_dir (str): The path of the output directory for saving the extracted documents and related files.
        max_workers (int, optional): The maximum number of worker processes in the process pool, default is 9.
    Returns:
        None: This function does not return a value but processes and saves the extraction results of all HTML files.
    """
    input_dir = Path(input_dir)  
    #output_dir = Path(output_dir)  
    html_files = list(input_dir.glob("*.html"))  

    with ProcessPoolExecutor(max_workers=max_workers) as executor:  
        futures = [executor.submit(test_process_single_html, html_path, Path(output_dir), pdf_path) for html_path in html_files]

        for future in as_completed(futures):  
            try:  
                future.result()  
            except Exception as e:  
                print(f"[ERROR] {e}")

def dummy_paper_fetch(input_file):
    base_dir = "orchestrator/"
    html_text_folder = os.path.join(base_dir, "htmls")
    pdf_folder_path = os.path.join(base_dir, "pdfs")
    image_folder_path = os.path.join(base_dir, "imgs")
    json_output_path = os.path.join(base_dir, "jsons")
    arxiv_pool_path = os.path.join(base_dir, "html_url_storage/html_urls.txt")
    os.makedirs(html_text_folder, exist_ok=True)
    os.makedirs(pdf_folder_path, exist_ok=True)
    os.makedirs(image_folder_path, exist_ok=True)
    os.makedirs(json_output_path, exist_ok=True)
    os.makedirs(os.path.dirname(arxiv_pool_path), exist_ok=True)
    
    # Enable this block to download HTML files from arXiv
    if False:
        extractor = ArxivPDFExtractor(None, pdf_folder_path, image_folder_path, arxiv_pool_path, json_output_path)
        extractor.extract_all()

    papers = []
    for filename in os.listdir(json_output_path):
        if filename.endswith(".json"):
            file_path = os.path.join(json_output_path, filename)
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                papers.append(DocSet.model_validate(data))
    return papers