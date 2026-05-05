import zipfile
import xml.etree.ElementTree as ET
import sys

pptx_file = 'd:\\Twitter_clone\\Twitter_prototype_presentation.pptx'

# The namespace for drawingML which contains the text
namespaces = {'a': 'http://schemas.openxmlformats.org/drawingml/2006/main'}

def extract_text_from_pptx(file_path):
    text_content = []
    try:
        with zipfile.ZipFile(file_path, 'r') as z:
            # Find all slide xml files
            slide_files = [f for f in z.namelist() if f.startswith('ppt/slides/slide') and f.endswith('.xml')]
            
            # Sort them so they are in order (slide1.xml, slide2.xml, etc.)
            slide_files.sort(key=lambda x: int(x.replace('ppt/slides/slide', '').replace('.xml', '')))
            
            for slide_file in slide_files:
                slide_content = z.read(slide_file)
                root = ET.fromstring(slide_content)
                slide_texts = []
                for node in root.findall('.//a:t', namespaces):
                    if node.text:
                        slide_texts.append(node.text)
                if slide_texts:
                    text_content.append(f"--- Slide {slide_files.index(slide_file) + 1} ---")
                    text_content.append("\n".join(slide_texts))
                    text_content.append("")
                    
        return "\n".join(text_content)
    except Exception as e:
        return str(e)

if __name__ == '__main__':
    result = extract_text_from_pptx(pptx_file)
    with open('extracted_text.txt', 'w', encoding='utf-8') as f:
        f.write(result)
    print("Extraction complete.")
