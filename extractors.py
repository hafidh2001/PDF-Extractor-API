"""
PDF text extraction and metadata parsing logic
"""
import PyPDF2
import re
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file"""
    try:
        text = ""
        with open(pdf_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            num_pages = len(pdf_reader.pages)
            
            for page_num in range(num_pages):
                page = pdf_reader.pages[page_num]
                text += page.extract_text()
        
        return text
    except Exception as e:
        logger.error(f"Error reading PDF {pdf_path}: {str(e)}")
        return ""


def extract_metadata(text: str, filename: str = "") -> Dict:
    """Extract metadata from PDF text using improved regex and heuristics"""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    
    metadata = {
        "judul": None,
        "penulis": None,
        "abstrak": None,
        "kata_kunci": []
    }
    
    # Clean lines from page numbers and headers
    cleaned_lines = []
    for line in lines:
        # Skip page numbers, headers, footers
        if re.match(r'^[\d\s]+$', line):  # Only numbers
            continue
        if re.match(r'^Page\s+\d+', line, re.IGNORECASE):
            continue
        # Skip very short lines (1-2 chars)
        if len(line) <= 2:
            continue
        cleaned_lines.append(line)
    
    lines = cleaned_lines
    
    # Extract metadata components
    metadata["judul"] = _extract_title(lines)
    metadata["penulis"] = _extract_authors(lines)
    metadata["abstrak"] = _extract_abstract(lines)
    metadata["kata_kunci"] = _extract_keywords(lines)
    
    return metadata


def _extract_title(lines: list) -> Optional[str]:
    """Extract title from PDF lines"""
    title_lines = []
    author_lines = []
    found_authors = False
    
    skip_words = ['universitas', 'fakultas', 'jurusan', 'program studi', 'issn', 'vol.', 'volume', 'jurnal', 'email', '@', 'doi:', 'http://', 'https://']
    
    for i, line in enumerate(lines[:50]):
        # Skip institutional headers and URLs
        if any(word in line.lower() for word in skip_words):
            continue
        
        # Skip lines that are clearly page numbers or headers
        if len(line) < 5 or line.isdigit():
            continue
            
        # Check if this looks like an author line - names with numbers and commas
        if re.search(r'[A-Z][a-z]+\s*\d+\s*,\s*[A-Z][a-z]+', line):
            # Confirm it's not part of the abstract
            if not any(word in line.lower() for word in ['pada', 'tahun', 'oleh', 'dengan', 'yang', 'abstrak']):
                author_lines.append(line)
                found_authors = True
                # Add affiliations
                for j in range(1, 3):
                    if i + j < len(lines):
                        next_line = lines[i + j]
                        if 'abstrak' in next_line.lower() or 'abstract' in next_line.lower():
                            break
                        if any(x in next_line.lower() for x in ['universitas', 'fakultas', 'manajemen', '@']):
                            author_lines.append(next_line)
                        else:
                            break
                continue
        
        # Collect title lines if we haven't found authors yet
        if not found_authors:
            if re.match(r'^\d{1,3}$', line):
                continue
            if re.match(r'^\d{4}$', line) or re.match(r'^[A-Z][a-z]+\s+\d{4}$', line):
                continue
            title_lines.append(line)
        elif found_authors:
            break
    
    # Process title - join all title lines
    if title_lines:
        title_text = " ".join(title_lines)
        title_text = re.sub(r'\s+', ' ', title_text).strip()
        title_text = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]+$', '', title_text).strip()
        return title_text
    
    return None


def _extract_authors(lines: list) -> Optional[str]:
    """Extract authors from PDF lines"""
    author_lines = []
    found_authors = False
    
    # Find author lines
    for i, line in enumerate(lines[:50]):
        if re.search(r'[A-Z][a-z]+\s*\d+\s*,\s*[A-Z][a-z]+', line):
            if not any(word in line.lower() for word in ['pada', 'tahun', 'oleh', 'dengan', 'yang', 'abstrak']):
                author_lines.append(line)
                found_authors = True
                # Check for affiliations
                for j in range(1, 3):
                    if i + j < len(lines):
                        next_line = lines[i + j]
                        if 'abstrak' in next_line.lower() or 'abstract' in next_line.lower():
                            break
                        if any(x in next_line.lower() for x in ['universitas', 'fakultas', 'manajemen', '@']):
                            author_lines.append(next_line)
                        else:
                            break
                break
    
    # Process authors
    if author_lines:
        authors = []
        for line in author_lines:
            # Skip pure affiliation lines
            if re.match(r'^(D4|S1|S2|S3|Manajemen|Fakultas)', line) or 'universitas' in line.lower():
                continue
            if '@' in line:
                continue
            
            # Remove superscript numbers and clean
            clean_line = re.sub(r'[¹²³⁴⁵⁶⁷⁸⁹]+', '', line)
            clean_line = re.sub(r'\d+', '', clean_line)
            
            # Split by comma and extract names
            parts = clean_line.split(',')
            for part in parts:
                part = part.strip()
                # Check if it looks like a name (Title Case)
                if re.match(r'^[A-Z][a-z]+(?:\s+[A-Z][a-z]*)*$', part) and len(part) > 2:
                    authors.append(part)
        
        if authors:
            # Remove duplicates while preserving order
            seen = set()
            unique_authors = []
            for author in authors:
                if author not in seen:
                    seen.add(author)
                    unique_authors.append(author)
            return ", ".join(unique_authors[:10])
    
    # Alternative approach if no authors found
    for i, line in enumerate(lines[:60]):
        if re.match(r'^[A-Z][a-z]+', line) and '@' not in line:
            names = re.findall(r'([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)', line)
            if names:
                names = [n for n in names if ' ' in n]
                if names:
                    return ", ".join(names[:10])
    
    return None


def _extract_abstract(lines: list) -> Optional[str]:
    """Extract abstract from PDF lines (take first one found - Indonesian or English)"""
    abstract_text = []
    abstract_start = None
    abstract_found = False
    
    for i, line in enumerate(lines):
        if abstract_found:
            break
            
        # Check for standalone abstract header
        if re.match(r'^(abstrak|abstract)\s*[-—:]?\s*$', line, re.IGNORECASE):
            abstract_start = i + 1
            abstract_found = True
            break
        # Check for abstract with dash or em-dash followed by content
        elif re.match(r'^(abstrak|abstract)\s*[-—]', line, re.IGNORECASE):
            abstract_content = re.sub(r'^(abstrak|abstract)\s*[-—]\s*', '', line, flags=re.IGNORECASE)
            if abstract_content:
                abstract_text.append(abstract_content)
            abstract_start = i + 1
            abstract_found = True
            break
    
    if abstract_start and abstract_start < len(lines):
        for i in range(abstract_start, min(abstract_start + 100, len(lines))):
            if i < len(lines):
                line = lines[i]
                # Stop conditions
                if re.match(r'^(kata[\s\-]?kunci|key[\s\-]?words?)\s*[-—:]', line, re.IGNORECASE):
                    break
                # Stop at another abstract (for bilingual papers)
                if re.match(r'^(abstrak|abstract)\s*[-—:]', line, re.IGNORECASE):
                    break
                if re.match(r'^(pendahuluan|introduction|latar belakang|^I\.\s|^1\.\s)', line, re.IGNORECASE):
                    break
                if len(line) > 5:
                    abstract_text.append(line)
    
    if abstract_text:
        full_abstract = " ".join(abstract_text)
        full_abstract = re.sub(r'\s+', ' ', full_abstract).strip()
        return full_abstract
    
    return None


def _extract_keywords(lines: list) -> list:
    """Extract keywords from PDF lines (take first one found - Indonesian or English)"""
    keywords_section = ""
    keywords_found = False
    
    for i, line in enumerate(lines):
        if keywords_found:
            break
            
        # Look for keywords header - can be at start OR after a period (inline)
        if re.search(r'(^|\.\s*)(kata[\s\-]?kunci|key[\s\-]?words?)\s*[-—:]', line, re.IGNORECASE):
            # Extract keywords after the separator
            keywords_section = re.sub(r'^.*(kata[\s\-]?kunci|key[\s\-]?words?)\s*[-—:]\s*', '', line, flags=re.IGNORECASE)
            
            # Check if keywords continue on next line
            if i + 1 < len(lines):
                next_line = lines[i + 1]
                if (',' in next_line or len(next_line) < 100) and \
                   not re.match(r'^(Abstract|Abstrak|Pendahuluan|Introduction|I\.|1\.|[A-Z][a-z]+ [a-z]+ [a-z]+)', next_line):
                    if keywords_section.rstrip().endswith(',') or not keywords_section.rstrip().endswith('.'):
                        keywords_section += " " + next_line
            
            keywords_found = True
            break
    
    if keywords_section:
        # Clean up
        keywords_section = keywords_section.rstrip('.')
        keywords_section = keywords_section.replace(";", ",")
        keywords_section = keywords_section.replace(" dan ", ", ")
        keywords_section = keywords_section.replace(" and ", ", ")
        
        # Split by comma and clean
        keywords = []
        for k in keywords_section.split(','):
            k = k.strip().rstrip('. ')
            word_count = len(k.split())
            if k and len(k) > 2 and len(k) < 100 and word_count <= 5:
                keywords.append(k)
        
        return keywords[:10]
    
    return []