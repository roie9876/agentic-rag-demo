#!/usr/bin/env python3
import os
import sys
from pathlib import Path

# Load environment manually
env_file = Path(__file__).resolve().parent / ".env"
if env_file.exists():
    with open(env_file, 'r') as f:
        for line in f:
            if '=' in line and not line.startswith('#'):
                key, value = line.strip().split('=', 1)
                while '${' in value and '}' in value:
                    start = value.find('${')
                    end = value.find('}', start)
                    if start != -1 and end != -1:
                        var_name = value[start+2:end]
                        var_value = os.environ.get(var_name, '')
                        value = value[:start] + var_value + value[end+1:]
                    else:
                        break
                os.environ[key] = value

sys.path.append(str(Path(__file__).resolve().parent))
from tools.doc_intelligence import DocumentIntelligenceClient

def analyze_figures_in_pdf(pdf_path: str):
    """Analyze what Document Intelligence detects about figures/images in the PDF"""
    
    print(f"🔍 Analyzing figures in: {os.path.basename(pdf_path)}")
    
    with open(pdf_path, 'rb') as f:
        file_bytes = f.read()
        
    client = DocumentIntelligenceClient()
    result, errors = client.analyze_document_from_bytes(
        file_bytes=file_bytes,
        filename=os.path.basename(pdf_path),
        model='prebuilt-layout'
    )
    
    if errors:
        print(f"❌ Errors: {errors}")
        return
        
    print(f"\n📊 DOCUMENT ANALYSIS RESULTS:")
    print(f"  📄 Total pages: {len(result.get('pages', []))}")
    
    # Check figures
    figures = result.get('figures', [])
    print(f"  🖼️  Total figures detected: {len(figures)}")
    
    if figures:
        print(f"\n🎨 FIGURE DETAILS:")
        for i, figure in enumerate(figures, 1):
            print(f"\n  📸 Figure {i}:")
            print(f"    🏷️  Caption: {figure.get('caption', 'No caption')}")
            print(f"    📄 Page: {figure.get('pageNumber', 'Unknown')}")
            print(f"    📐 Bounding box: {figure.get('boundingRegions', 'Not specified')}")
            print(f"    🔗 Elements: {len(figure.get('elements', []))} elements")
            
            # Check if there's image data
            if 'content' in figure:
                content_preview = str(figure['content'])[:100] + "..." if len(str(figure['content'])) > 100 else str(figure['content'])
                print(f"    📝 Content: {content_preview}")
            
            # Print all available keys for this figure
            print(f"    🔑 Available data: {list(figure.keys())}")
    
    # Check paragraphs that might reference images
    paragraphs = result.get('paragraphs', [])
    image_related_paragraphs = []
    
    for para in paragraphs:
        content = para.get('content', '').lower()
        if any(word in content for word in ['תמונה', 'דמות', 'איור', 'צילום', 'image', 'figure', 'photo']):
            image_related_paragraphs.append(para.get('content', ''))
    
    if image_related_paragraphs:
        print(f"\n🖼️  PARAGRAPHS REFERENCING IMAGES ({len(image_related_paragraphs)}):")
        for i, para in enumerate(image_related_paragraphs[:3], 1):  # Show first 3
            preview = para[:150] + "..." if len(para) > 150 else para
            print(f"  {i}. {preview}")
    
    # Check content format for embedded images
    content = result.get('content', '')
    if '<figure>' in content:
        print(f"\n📑 CONTENT CONTAINS FIGURE TAGS:")
        # Extract figure sections
        import re
        figure_matches = re.findall(r'<figure>.*?</figure>', content, re.DOTALL)
        print(f"  🏷️  Found {len(figure_matches)} figure sections in content")
        
        for i, fig_content in enumerate(figure_matches[:2], 1):  # Show first 2
            preview = fig_content[:200] + "..." if len(fig_content) > 200 else fig_content
            print(f"  📸 Figure {i}: {repr(preview)}")

if __name__ == "__main__":
    pdf_path = "/Users/robenhai/Downloads/תעשייה אווירית – ויקיפדיה.pdf"
    if os.path.exists(pdf_path):
        analyze_figures_in_pdf(pdf_path)
    else:
        print("❌ Test PDF not found")
