import json
import os
import sys
from datetime import datetime
from pdf_parser import parse_pdf_to_chunks
from semantic_searcher import SemanticSearcher


def generate_persona_query(persona: str, job_to_be_done: str) -> str:
    """Generates a dynamic query based on persona and job."""
    base_query = f"As a {persona}, I need to {job_to_be_done}. "

    # Keyword mapping for different personas
    persona_keywords = {
        "Travel Planner": "planning, itinerary, schedule, activities, budget, accommodation, attractions, transportation, destinations, tours, booking, travel tips",
        "Food Contractor": "menu planning, food preparation, catering services, ingredient sourcing, kitchen operations, food safety, nutrition, cost management, supplier relations, quality control",
        "HR Professional": "employee management, recruitment, policy compliance, training programs, performance evaluation, workplace procedures, staff development, benefits administration, labor relations",
        "Researcher": "methodology, data analysis, findings, literature review, results, study design, experimental procedures",
        "Financial Analyst": "revenue analysis, profit margins, investment strategies, financial forecasting, risk assessment, market performance",
        "Investment Analyst": "market analysis, portfolio management, investment returns, valuation methods, growth opportunities"
    }

    # Default keywords if persona is not in the map
    default_keywords = "relevant information, key insights, actionable details"

    # Find the most relevant persona key
    best_match = None
    for key in persona_keywords:
        if key.lower() in persona.lower():
            best_match = key
            break

    keywords = persona_keywords.get(best_match, default_keywords)

    return base_query + f"Focus on information related to {keywords}. Provide actionable insights that help me organize or coordinate or arrange the relevant aspects. Prioritize practical, detailed information over general overviews."


def run_analysis(collection_dir: str):
    """
    Executes the full analysis pipeline for a given document collection.
    """
    input_json_path = os.path.join(collection_dir, 'challenge1b_input.json')
    pdfs_dir = os.path.join(collection_dir, 'PDFs')
    output_json_path = os.path.join(collection_dir, 'challenge1b_output.json')

    if not os.path.isfile(input_json_path):
        print(f"Error: Input file not found at {input_json_path}")
        return

    with open(input_json_path, 'r') as f:
        input_data = json.load(f)

    persona = input_data['persona']['role']
    job_to_be_done = input_data['job_to_be_done']['task']
    documents_to_process = input_data['documents']

    # Use the dynamic query generator
    query = generate_persona_query(persona, job_to_be_done)
    print(f"INFO: Generated Query: '{query}'")

    all_chunks = []
    print("INFO: Parsing specified PDF documents...")
    for doc_info in documents_to_process:
        pdf_filename = doc_info['filename']
        pdf_path = os.path.join(pdfs_dir, pdf_filename)
        if os.path.exists(pdf_path):
            chunks = parse_pdf_to_chunks(pdf_path, pdf_filename)
            if chunks:
                all_chunks.extend(chunks)
        else:
            print(f"WARNING: Could not find {pdf_filename} in {pdfs_dir}. Skipping.")

    if not all_chunks:
        print("Error: No text could be extracted from any PDFs. Cannot proceed.")
        return

    # Try multiple model paths
    model_paths = [
        'models/all-MiniLM-L6-v2',
        '../models/all-MiniLM-L6-v2',
        './models/all-MiniLM-L6-v2'
    ]

    model_path = None
    for path in model_paths:
        if os.path.exists(path):
            model_path = path
            break

    if not model_path:
        print(f"FATAL: Model not found at any of the searched paths: {model_paths}")
        print("Please ensure the model is downloaded and placed in the correct directory.")
        sys.exit(1)

    print("INFO: Initializing semantic searcher...")
    searcher = SemanticSearcher(model_path=model_path)

    print("INFO: Finding and ranking relevant sections...")
    # Pass persona to the ranking function for persona-aware scoring
    ranked_results = searcher.rank_chunks(query, all_chunks, persona)

    print("INFO: Filtering for unique and diverse results...")
    final_results = []
    seen_texts = set()
    doc_counts = {}
    MAX_HITS_PER_DOC = 3  # Enforcing diversity

    for result in ranked_results:
        doc_name = result['document']
        if doc_name not in doc_counts:
            doc_counts[doc_name] = 0

        if result['text'] not in seen_texts and doc_counts[doc_name] < MAX_HITS_PER_DOC:
            final_results.append(result)
            seen_texts.add(result['text'])
            doc_counts[doc_name] += 1

    top_n_results = 20
    final_results = final_results[:top_n_results]

    for i, result in enumerate(final_results):
        result['importance_rank'] = i + 1

    extracted_sections = [
        {
            "document": result['document'],
            "section_title": result['section_title'],
            "importance_rank": result['importance_rank'],
            "page_number": result['page_number']
        }
        for result in final_results
    ]

    subsection_analysis = [
        {
            "document": result['document'],
            "refined_text": result['text'],
            "page_number": result['page_number']
        }
        for result in final_results
    ]

    output_data = {
        "metadata": {
            "input_documents": [doc['filename'] for doc in documents_to_process],
            "persona": persona,
            "job_to_be_done": job_to_be_done,
            "generated_query": query,
            "total_chunks_processed": len(all_chunks),
            "diversity_enforced": True
        },
        "extracted_sections": extracted_sections,
        "subsection_analysis": subsection_analysis
    }

    # Add timestamp to metadata
    output_data["metadata"]["processed_time"] = datetime.utcnow().isoformat() + "Z"

    with open(output_json_path, 'w') as f:
        json.dump(output_data, f, indent=2)

    print(f"SUCCESS: Analysis complete. Output written to {output_json_path}")


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python src/main.py <path_to_collection_directory>")
        sys.exit(1)

    collection_directory = sys.argv[1]
    run_analysis(collection_directory)
