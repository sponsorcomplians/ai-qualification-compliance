from flask import Blueprint, request, jsonify
from models.compliance import Worker, Qualification, QualificationTemplate, db
import json
import random

ai_agent_bp = Blueprint('ai_agent', __name__)

@ai_agent_bp.route('/query', methods=['POST'])
def ai_query():
    """Handle AI agent queries about compliance"""
    try:
        data = request.get_json()
        query = data.get('query', '').lower()
        
        # Simple AI response logic based on query content
        response = generate_ai_response(query)
        
        return jsonify({
            'success': True,
            'data': {
                'query': data.get('query'),
                'response': response['answer'],
                'confidence': response['confidence'],
                'sources': response['sources']
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def generate_ai_response(query):
    """Generate AI response based on query"""
    
    # Healthcare qualification queries
    if any(keyword in query for keyword in ['qualification', 'senior care', 'soc 6146', 'care worker']):
        return {
            'answer': 'For Senior Care Worker roles (SOC Code 6146), workers typically need relevant healthcare qualifications such as Level 3 Diploma in Health and Social Care, NVQ Level 3 in Health and Social Care, or equivalent qualifications. The qualification must be completed before the Certificate of Sponsorship assignment date.',
            'confidence': 0.90,
            'sources': ['Paragraph C1.38', 'SOC Code 6146 Requirements']
        }
    
    # Compliance assessment queries
    elif any(keyword in query for keyword in ['compliance', 'breach', 'paragraph c1.38']):
        return {
            'answer': 'Paragraph C1.38 requires sponsors to ensure workers have necessary qualifications, experience, or immigration permission for their role. Breaches occur when: 1) No relevant qualifications, 2) Qualifications obtained after CoS assignment, 3) No certificate evidence on file.',
            'confidence': 0.95,
            'sources': ['Workers and Temporary Workers Guidance', 'Paragraph C1.38']
        }
    
    # Evidence requirements
    elif any(keyword in query for keyword in ['evidence', 'certificate', 'documentation']):
        return {
            'answer': 'Sponsors must retain evidence of worker qualifications including: qualification certificates, CV/application forms mentioning qualifications, and verification documents. All evidence must demonstrate the worker was qualified at the time of sponsorship.',
            'confidence': 0.88,
            'sources': ['Sponsor Duties', 'Record Keeping Requirements']
        }
    
    # Risk assessment queries
    elif any(keyword in query for keyword in ['risk', 'assessment', 'scoring']):
        return {
            'answer': 'Risk scoring considers: qualification relevance (40%), timing vs CoS date (30%), evidence availability (20%), and consistency across documents (10%). Scores range from 0 (critical risk) to 10 (fully compliant).',
            'confidence': 0.85,
            'sources': ['Internal Risk Framework', 'Compliance Assessment Guidelines']
        }
    
    # Default response
    else:
        return {
            'answer': 'I can help with qualification compliance questions, Paragraph C1.38 requirements, evidence documentation, and risk assessments. Please ask about specific compliance topics for detailed guidance.',
            'confidence': 0.70,
            'sources': ['General Compliance Knowledge']
        }

@ai_agent_bp.route('/health', methods=['GET'])
def health_check():
    """Health check for AI agent"""
    return jsonify({'status': 'healthy', 'service': 'AI Agent'})
