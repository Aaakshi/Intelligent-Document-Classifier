
import spacy
import os
import PyPDF2
import docx
from PIL import Image
import pytesseract
import magic
import hashlib
from typing import Dict, Any

class DocumentClassifier:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("spaCy English model not found. Please install it with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Document type keywords and patterns
        self.doc_type_patterns = {
            'contract': [
                'agreement', 'contract', 'terms and conditions', 'whereas', 'party',
                'consideration', 'obligations', 'covenant', 'liability', 'termination'
            ],
            'invoice': [
                'invoice', 'bill', 'amount due', 'total amount', 'payment terms',
                'due date', 'invoice number', 'billing address', 'tax', 'subtotal'
            ],
            'report': [
                'report', 'analysis', 'findings', 'conclusions', 'recommendations',
                'methodology', 'results', 'summary', 'overview', 'executive summary'
            ],
            'correspondence': [
                'dear', 'sincerely', 'best regards', 'yours truly', 'letter',
                'email', 'memorandum', 'memo', 'communication', 'follow up'
            ],
            'legal': [
                'whereas', 'plaintiff', 'defendant', 'court', 'judgment', 'statute',
                'regulation', 'compliance', 'legal notice', 'litigation', 'appeal'
            ],
            'financial': [
                'balance sheet', 'income statement', 'cash flow', 'assets', 'liabilities',
                'revenue', 'expenses', 'profit', 'financial', 'accounting'
            ],
            'hr': [
                'employee', 'personnel', 'human resources', 'payroll', 'benefits',
                'performance review', 'job description', 'recruitment', 'training'
            ],
            'technical': [
                'specification', 'requirements', 'architecture', 'design', 'implementation',
                'testing', 'documentation', 'technical', 'system', 'software'
            ]
        }
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text from various file formats"""
        try:
            # Detect file type
            mime_type = magic.from_file(file_path, mime=True)
            
            if mime_type == 'application/pdf':
                return self._extract_from_pdf(file_path)
            elif mime_type in ['application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                              'application/msword']:
                return self._extract_from_docx(file_path)
            elif mime_type.startswith('image/'):
                return self._extract_from_image(file_path)
            elif mime_type.startswith('text/'):
                return self._extract_from_text(file_path)
            else:
                return ""
        except Exception as e:
            print(f"Error extracting text from {file_path}: {e}")
            return ""
    
    def _extract_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error extracting from PDF: {e}")
            return ""
    
    def _extract_from_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting from DOCX: {e}")
            return ""
    
    def _extract_from_image(self, file_path: str) -> str:
        """Extract text from image using OCR"""
        try:
            image = Image.open(file_path)
            text = pytesseract.image_to_string(image)
            return text
        except Exception as e:
            print(f"Error extracting from image: {e}")
            return ""
    
    def _extract_from_text(self, file_path: str) -> str:
        """Extract text from plain text file"""
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                return file.read()
        except Exception as e:
            print(f"Error extracting from text file: {e}")
            return ""
    
    def classify_document(self, file_path: str) -> Dict[str, Any]:
        """Classify document and return type with confidence score"""
        
        # Extract text from document
        text = self.extract_text_from_file(file_path)
        
        if not text.strip():
            return {
                'doc_type': 'unknown',
                'confidence': 0.0,
                'priority': 1,
                'extracted_text': text
            }
        
        # Convert to lowercase for pattern matching
        text_lower = text.lower()
        
        # Score each document type
        type_scores = {}
        
        for doc_type, keywords in self.doc_type_patterns.items():
            score = 0
            total_keywords = len(keywords)
            
            for keyword in keywords:
                if keyword in text_lower:
                    # Weight longer keywords more heavily
                    weight = len(keyword.split())
                    score += weight
            
            # Normalize score
            type_scores[doc_type] = score / (total_keywords * 2)  # Max weight is 2 for two-word phrases
        
        # Find the highest scoring type
        if type_scores:
            best_type = max(type_scores, key=type_scores.get)
            confidence = min(type_scores[best_type], 1.0)  # Cap at 1.0
        else:
            best_type = 'unknown'
            confidence = 0.0
        
        # Determine priority based on document type and content
        priority = self._determine_priority(best_type, text_lower)
        
        return {
            'doc_type': best_type,
            'confidence': confidence,
            'priority': priority,
            'extracted_text': text[:1000],  # First 1000 characters
            'type_scores': type_scores
        }
    
    def _determine_priority(self, doc_type: str, text: str) -> int:
        """Determine document priority (1-5, where 5 is highest)"""
        
        # High priority keywords
        urgent_keywords = ['urgent', 'asap', 'immediate', 'critical', 'emergency', 'deadline']
        
        # Check for urgent keywords
        if any(keyword in text for keyword in urgent_keywords):
            return 5
        
        # Priority based on document type
        type_priorities = {
            'legal': 4,
            'contract': 4,
            'invoice': 3,
            'financial': 3,
            'hr': 2,
            'correspondence': 2,
            'report': 2,
            'technical': 1,
            'unknown': 1
        }
        
        return type_priorities.get(doc_type, 1)
    
    def get_document_hash(self, file_path: str) -> str:
        """Generate hash for document content"""
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()
        except Exception as e:
            print(f"Error generating hash for {file_path}: {e}")
            return ""
