
import spacy
import re
from typing import Dict, Any, List
from datetime import datetime
import openai
import os

class ContentAnalyzer:
    def __init__(self):
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("spaCy English model not found")
            self.nlp = None
        
        # Set OpenAI API key if available
        openai.api_key = os.getenv("OPENAI_API_KEY")
        
        # Risk keywords for compliance scanning
        self.risk_keywords = {
            'high_risk': ['confidential', 'classified', 'restricted', 'private', 'sensitive'],
            'financial_risk': ['payment', 'credit card', 'ssn', 'social security', 'bank account'],
            'legal_risk': ['lawsuit', 'litigation', 'breach', 'violation', 'penalty'],
            'compliance_risk': ['gdpr', 'hipaa', 'sox', 'regulation', 'compliance']
        }
    
    def analyze_content(self, file_path: str) -> Dict[str, Any]:
        """Perform comprehensive content analysis"""
        
        # Import classifier to get extracted text
        from .classifier import DocumentClassifier
        classifier = DocumentClassifier()
        text = classifier.extract_text_from_file(file_path)
        
        if not text.strip():
            return self._empty_analysis()
        
        analysis = {}
        
        # Extract entities
        analysis['entities'] = self._extract_entities(text)
        
        # Generate summary
        analysis['summary'] = self._generate_summary(text)
        
        # Detect language
        analysis['language'] = self._detect_language(text)
        
        # Analyze sentiment
        analysis['sentiment'] = self._analyze_sentiment(text)
        
        # Extract topics
        analysis['topics'] = self._extract_topics(text)
        
        # Assess risk
        analysis['risk_score'] = self._assess_risk(text)
        
        # Find related patterns
        analysis['patterns'] = self._find_patterns(text)
        
        return analysis
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text"""
        entities = {
            'persons': [],
            'organizations': [],
            'dates': [],
            'money': [],
            'locations': [],
            'emails': [],
            'phone_numbers': []
        }
        
        if self.nlp:
            doc = self.nlp(text)
            
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    entities['persons'].append(ent.text)
                elif ent.label_ == "ORG":
                    entities['organizations'].append(ent.text)
                elif ent.label_ == "DATE":
                    entities['dates'].append(ent.text)
                elif ent.label_ == "MONEY":
                    entities['money'].append(ent.text)
                elif ent.label_ in ["GPE", "LOC"]:
                    entities['locations'].append(ent.text)
        
        # Extract emails using regex
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        entities['emails'] = re.findall(email_pattern, text)
        
        # Extract phone numbers using regex
        phone_pattern = r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'
        entities['phone_numbers'] = re.findall(phone_pattern, text)
        
        # Remove duplicates and limit results
        for key in entities:
            entities[key] = list(set(entities[key]))[:10]  # Limit to 10 items
        
        return entities
    
    def _generate_summary(self, text: str) -> str:
        """Generate document summary"""
        # If OpenAI is available, use it for better summaries
        if openai.api_key and len(text) > 100:
            try:
                response = openai.ChatCompletion.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {"role": "user", "content": f"Summarize this document in 2-3 sentences:\n\n{text[:2000]}"}
                    ],
                    max_tokens=150
                )
                return response.choices[0].message.content.strip()
            except Exception as e:
                print(f"OpenAI summarization failed: {e}")
        
        # Fallback: Simple extractive summary
        sentences = text.split('. ')
        if len(sentences) <= 3:
            return text[:500]
        
        # Take first and last sentences, plus one from middle
        summary_sentences = [
            sentences[0],
            sentences[len(sentences)//2],
            sentences[-1]
        ]
        
        return '. '.join(summary_sentences)[:500]
    
    def _detect_language(self, text: str) -> str:
        """Detect document language"""
        # Simple language detection based on common words
        english_words = ['the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by']
        spanish_words = ['el', 'la', 'los', 'las', 'y', 'o', 'pero', 'en', 'de', 'con', 'por', 'para']
        french_words = ['le', 'la', 'les', 'et', 'ou', 'mais', 'dans', 'de', 'avec', 'par', 'pour']
        
        text_lower = text.lower()
        
        en_count = sum(1 for word in english_words if word in text_lower)
        es_count = sum(1 for word in spanish_words if word in text_lower)
        fr_count = sum(1 for word in french_words if word in text_lower)
        
        if en_count >= es_count and en_count >= fr_count:
            return 'en'
        elif es_count >= fr_count:
            return 'es'
        elif fr_count > 0:
            return 'fr'
        else:
            return 'en'  # Default to English
    
    def _analyze_sentiment(self, text: str) -> float:
        """Analyze sentiment of the document"""
        # Simple sentiment analysis using keyword matching
        positive_words = ['good', 'excellent', 'great', 'positive', 'success', 'approve', 'agree']
        negative_words = ['bad', 'terrible', 'negative', 'fail', 'reject', 'disagree', 'problem']
        
        text_lower = text.lower()
        
        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)
        
        total_words = len(text.split())
        
        if total_words == 0:
            return 0.0
        
        # Calculate sentiment score between -1 and 1
        sentiment_score = (positive_count - negative_count) / max(total_words / 100, 1)
        return max(-1, min(1, sentiment_score))
    
    def _extract_topics(self, text: str) -> Dict[str, float]:
        """Extract main topics from document"""
        topics = {
            'business': 0,
            'legal': 0,
            'financial': 0,
            'technical': 0,
            'personal': 0
        }
        
        topic_keywords = {
            'business': ['business', 'company', 'corporate', 'meeting', 'strategy', 'market'],
            'legal': ['legal', 'law', 'court', 'judge', 'attorney', 'contract', 'agreement'],
            'financial': ['money', 'payment', 'invoice', 'budget', 'cost', 'price', 'financial'],
            'technical': ['technical', 'software', 'system', 'development', 'programming', 'data'],
            'personal': ['personal', 'private', 'individual', 'family', 'personal']
        }
        
        text_lower = text.lower()
        total_words = len(text.split())
        
        for topic, keywords in topic_keywords.items():
            count = sum(1 for keyword in keywords if keyword in text_lower)
            topics[topic] = count / max(total_words / 100, 1)
        
        return topics
    
    def _assess_risk(self, text: str) -> float:
        """Assess compliance and security risk"""
        risk_score = 0.0
        text_lower = text.lower()
        
        for risk_category, keywords in self.risk_keywords.items():
            category_score = sum(1 for keyword in keywords if keyword in text_lower)
            
            # Weight different risk categories
            if risk_category == 'high_risk':
                risk_score += category_score * 0.4
            elif risk_category == 'financial_risk':
                risk_score += category_score * 0.3
            elif risk_category == 'legal_risk':
                risk_score += category_score * 0.2
            elif risk_category == 'compliance_risk':
                risk_score += category_score * 0.1
        
        # Normalize to 0-1 scale
        return min(1.0, risk_score / 10)
    
    def _find_patterns(self, text: str) -> Dict[str, List[str]]:
        """Find common patterns in document"""
        patterns = {
            'dates': [],
            'amounts': [],
            'references': [],
            'urls': []
        }
        
        # Date patterns
        date_patterns = [
            r'\d{1,2}/\d{1,2}/\d{4}',
            r'\d{1,2}-\d{1,2}-\d{4}',
            r'\b\d{1,2}\s+\w+\s+\d{4}\b'
        ]
        
        for pattern in date_patterns:
            patterns['dates'].extend(re.findall(pattern, text))
        
        # Amount patterns
        amount_patterns = [
            r'\$\d+(?:,\d{3})*(?:\.\d{2})?',
            r'\d+(?:,\d{3})*(?:\.\d{2})?\s*(?:USD|dollars)',
        ]
        
        for pattern in amount_patterns:
            patterns['amounts'].extend(re.findall(pattern, text))
        
        # Reference patterns
        ref_pattern = r'\b(?:REF|Reference|ID|Number):\s*([A-Z0-9-]+)\b'
        patterns['references'] = re.findall(ref_pattern, text, re.IGNORECASE)
        
        # URL patterns
        url_pattern = r'https?://[^\s]+'
        patterns['urls'] = re.findall(url_pattern, text)
        
        # Limit results
        for key in patterns:
            patterns[key] = patterns[key][:5]
        
        return patterns
    
    def _empty_analysis(self) -> Dict[str, Any]:
        """Return empty analysis structure"""
        return {
            'entities': {'persons': [], 'organizations': [], 'dates': [], 'money': [], 'locations': [], 'emails': [], 'phone_numbers': []},
            'summary': '',
            'language': 'en',
            'sentiment': 0.0,
            'topics': {'business': 0, 'legal': 0, 'financial': 0, 'technical': 0, 'personal': 0},
            'risk_score': 0.0,
            'patterns': {'dates': [], 'amounts': [], 'references': [], 'urls': []}
        }
