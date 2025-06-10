import PyPDF2
import docx
import re
from datetime import datetime
from dateutil import parser
import json
from typing import Dict, List, Tuple, Optional

class AIDocumentProcessor:
    def __init__(self):
        # Healthcare qualifications from your compliance template
        self.healthcare_qualifications = [
            "Level 2 Diploma in Care",
            "Level 3 Diploma in Health and Social Care",
            "Level 3 Diploma in Adult Care", 
            "Level 4 Diploma in Adult Care",
            "Level 5 Diploma in Leadership for Health and Social Care",
            "Level 5 Diploma in Leadership and Management for Adult Care",
            "Level 4 Certificate in Principles of Leadership and Management in Adult Care",
            "NVQ Level 3 in Health and Social Care",
            "NVQ Level 4 in Health and Social Care",
            "SVQ Level 3 in Health and Social Care",
            "SVQ Level 4 in Health and Social Care",
            "Care Certificate",
            "Diploma in Dementia Care",
            "Certificate in Palliative Care",
            "Certificate in End-of-Life Care",
            "Certificate in Understanding Dignity and Safeguarding",
            "Certificate in Principles of Working with Individuals with Learning Disabilities",
            "Certificate in Mental Health Awareness",
            "Certificate in Infection Prevention and Control",
            "Bachelor of Science in Nursing",
            "BSc Nursing",
            "Diploma in General Nursing & Midwifery",
            "GNM",
            "Diploma in Health and Social Care",
            "Bachelor of Social Work",
            "BSW",
            "Certificate in Caregiving",
            "Higher National Diploma in Health and Social Care",
            "HND"
        ]
        
        # SOC codes that require healthcare qualifications
        self.healthcare_soc_codes = ["6146"]  # Senior Carer
    
    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
        except Exception as e:
            print(f"Error extracting PDF text: {e}")
            return ""
    
    def extract_text_from_docx(self, file_path: str) -> str:
        """Extract text from Word document"""
        try:
            doc = docx.Document(file_path)
            text = ""
            for paragraph in doc.paragraphs:
                text += paragraph.text + "\n"
            return text
        except Exception as e:
            print(f"Error extracting DOCX text: {e}")
            return ""
    
    def extract_text_from_file(self, file_path: str) -> str:
        """Extract text based on file extension"""
        if file_path.lower().endswith('.pdf'):
            return self.extract_text_from_pdf(file_path)
        elif file_path.lower().endswith(('.docx', '.doc')):
            return self.extract_text_from_docx(file_path)
        else:
            return ""
    
    def extract_dates(self, text: str) -> List[datetime]:
        """Extract dates from text"""
        dates = []
        # Common date patterns
        date_patterns = [
            r'\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b',  # DD/MM/YYYY or MM/DD/YYYY
            r'\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b',  # YYYY/MM/DD
            r'\b\d{1,2}\s+(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
            r'\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}\b',
            r'\b\d{4}\b'  # Just year
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    if re.match(r'^\d{4}$', match):  # Just year
                        dates.append(datetime(int(match), 1, 1))
                    else:
                        parsed_date = parser.parse(match, fuzzy=True)
                        dates.append(parsed_date)
                except:
                    continue
        
        return dates
    
    def find_qualifications(self, text: str) -> List[Dict]:
        """Find healthcare qualifications mentioned in text"""
        found_qualifications = []
        text_lower = text.lower()
        
        for qual in self.healthcare_qualifications:
            qual_lower = qual.lower()
            if qual_lower in text_lower:
                # Try to find dates near this qualification
                qual_index = text_lower.find(qual_lower)
                surrounding_text = text[max(0, qual_index-200):qual_index+200]
                dates = self.extract_dates(surrounding_text)
                
                found_qualifications.append({
                    'qualification': qual,
                    'found_in_text': True,
                    'surrounding_text': surrounding_text,
                    'potential_dates': [d.strftime('%Y-%m-%d') for d in dates]
                })
        
        return found_qualifications
    
    def extract_cos_info(self, text: str) -> Dict:
        """Extract Certificate of Sponsorship information"""
        cos_info = {}
        
        # Extract CoS reference number
        cos_patterns = [
            r'CoS\s*(?:Reference|Number|Ref)?\s*:?\s*([A-Z0-9]+)',
            r'Certificate\s+of\s+Sponsorship\s*:?\s*([A-Z0-9]+)',
            r'Sponsorship\s*(?:Reference|Number|Ref)?\s*:?\s*([A-Z0-9]+)'
        ]
        
        for pattern in cos_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cos_info['cos_reference'] = match.group(1)
                break
        
        # Extract SOC code
        soc_patterns = [
            r'SOC\s*(?:Code)?\s*:?\s*(\d{4})',
            r'Standard\s+Occupational\s+Classification\s*:?\s*(\d{4})'
        ]
        
        for pattern in soc_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cos_info['soc_code'] = match.group(1)
                break
        
        # Extract job title
        job_patterns = [
            r'Job\s+Title\s*:?\s*([^\n\r]+)',
            r'Position\s*:?\s*([^\n\r]+)',
            r'Role\s*:?\s*([^\n\r]+)'
        ]
        
        for pattern in job_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                cos_info['job_title'] = match.group(1).strip()
                break
        
        # Extract assignment date
        assignment_patterns = [
            r'Assignment\s+Date\s*:?\s*([^\n\r]+)',
            r'CoS\s+(?:Assignment|Assigned)\s*:?\s*([^\n\r]+)',
            r'Date\s+Assigned\s*:?\s*([^\n\r]+)'
        ]
        
        for pattern in assignment_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    cos_info['assignment_date'] = parser.parse(match.group(1), fuzzy=True).strftime('%Y-%m-%d')
                except:
                    cos_info['assignment_date'] = match.group(1).strip()
                break
        
        return cos_info
    
    def assess_compliance(self, documents_analysis: Dict) -> Dict:
        """Assess compliance based on Paragraph C1.38 logic"""
        assessment = {
            'compliance_status': 'UNKNOWN',
            'risk_level': 'HIGH',
            'findings': [],
            'recommendations': [],
            'breach_type': None
        }
        
        cos_info = documents_analysis.get('cos_document', {})
        cv_qualifications = documents_analysis.get('cv_document', {}).get('qualifications', [])
        application_qualifications = documents_analysis.get('application_document', {}).get('qualifications', [])
        certificate_qualifications = documents_analysis.get('certificate_documents', [])
        
        # Get CoS assignment date
        cos_assignment_date = None
        if cos_info.get('assignment_date'):
            try:
                cos_assignment_date = parser.parse(cos_info['assignment_date'])
            except:
                pass
        
        # Check if role requires healthcare qualifications
        soc_code = cos_info.get('soc_code')
        requires_healthcare_qual = soc_code in self.healthcare_soc_codes
        
        if not requires_healthcare_qual:
            assessment['compliance_status'] = 'NOT_APPLICABLE'
            assessment['risk_level'] = 'LOW'
            assessment['findings'].append("Role does not require specific healthcare qualifications")
            return assessment
        
        # Find all relevant qualifications
        all_qualifications = cv_qualifications + application_qualifications + certificate_qualifications
        relevant_qualifications = [q for q in all_qualifications if q.get('found_in_text')]
        
        # OUTCOME 1: No relevant qualification at all
        if not relevant_qualifications:
            assessment['compliance_status'] = 'SERIOUS_BREACH'
            assessment['risk_level'] = 'CRITICAL'
            assessment['breach_type'] = 'NO_QUALIFICATION'
            assessment['findings'].append("No relevant healthcare qualification found in any document")
            assessment['recommendations'].append("Immediate action required - worker lacks required qualifications")
            return assessment
        
        # Check qualification timing and evidence
        compliant_qualifications = []
        post_cos_qualifications = []
        no_evidence_qualifications = []
        
        for qual in relevant_qualifications:
            has_certificate = any('certificate' in doc_type.lower() 
                                for doc_type in documents_analysis.keys() 
                                if qual in documents_analysis[doc_type].get('qualifications', []))
            
            # Check if qualification was completed before CoS
            qual_dates = qual.get('potential_dates', [])
            if qual_dates and cos_assignment_date:
                qual_date = parser.parse(qual_dates[0])
                if qual_date <= cos_assignment_date:
                    if has_certificate:
                        compliant_qualifications.append(qual)
                    else:
                        no_evidence_qualifications.append(qual)
                else:
                    post_cos_qualifications.append(qual)
            else:
                if has_certificate:
                    compliant_qualifications.append(qual)
                else:
                    no_evidence_qualifications.append(qual)
        
        # OUTCOME 2: Qualification obtained after CoS assigned
        if post_cos_qualifications and not compliant_qualifications:
            assessment['compliance_status'] = 'BREACH'
            assessment['risk_level'] = 'HIGH'
            assessment['breach_type'] = 'POST_COS_QUALIFICATION'
            assessment['findings'].append("Relevant qualification was obtained after CoS assignment")
            assessment['recommendations'].append("Review sponsorship decision - qualification not valid at time of sponsorship")
            return assessment
        
        # OUTCOME 3: No certificate on file
        if no_evidence_qualifications and not compliant_qualifications:
            assessment['compliance_status'] = 'BREACH'
            assessment['risk_level'] = 'HIGH'
            assessment['breach_type'] = 'NO_EVIDENCE'
            assessment['findings'].append("Relevant qualification claimed but no certificate evidence available")
            assessment['recommendations'].append("Obtain and file qualification certificates immediately")
            return assessment
        
        # FULLY COMPLIANT
        if compliant_qualifications:
            assessment['compliance_status'] = 'COMPLIANT'
            assessment['risk_level'] = 'LOW'
            assessment['findings'].append(f"Found {len(compliant_qualifications)} relevant qualification(s) with evidence")
            assessment['recommendations'].append("Maintain current documentation standards")
            return assessment
        
        return assessment
