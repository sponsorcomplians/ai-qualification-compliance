from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Worker(db.Model):
    """Model for sponsored workers"""
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(255), nullable=False)
    cos_reference = db.Column(db.String(50), unique=True, nullable=False)
    job_title = db.Column(db.String(255), nullable=False)
    soc_code = db.Column(db.String(10), nullable=False)
    cos_assignment_date = db.Column(db.Date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    qualifications = db.relationship('Qualification', backref='worker', lazy=True, cascade='all, delete-orphan')
    assessments = db.relationship('Assessment', backref='worker', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Worker {self.full_name} - {self.cos_reference}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.full_name,
            'cos_reference': self.cos_reference,
            'job_title': self.job_title,
            'soc_code': self.soc_code,
            'cos_assignment_date': self.cos_assignment_date.isoformat() if self.cos_assignment_date else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Qualification(db.Model):
    """Model for worker qualifications"""
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    title = db.Column(db.String(500), nullable=False)
    level = db.Column(db.String(50))
    completion_date = db.Column(db.Date, nullable=False)
    issuing_institution = db.Column(db.String(255))
    certificate_number = db.Column(db.String(100))
    verification_status = db.Column(db.String(50), default='pending')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Qualification {self.title} - {self.worker.full_name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'worker_id': self.worker_id,
            'title': self.title,
            'level': self.level,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'issuing_institution': self.issuing_institution,
            'certificate_number': self.certificate_number,
            'verification_status': self.verification_status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Assessment(db.Model):
    """Model for compliance assessments"""
    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('worker.id'), nullable=False)
    assessment_date = db.Column(db.DateTime, default=datetime.utcnow)
    compliance_status = db.Column(db.String(50), nullable=False)  # 'compliant', 'breach', 'serious_breach'
    risk_score = db.Column(db.Integer)  # 0-10 scale
    assessment_outcome = db.Column(db.Text)
    recommendations = db.Column(db.Text)  # JSON string of recommendations
    assessed_by = db.Column(db.String(100))
    ai_confidence_score = db.Column(db.Float)
    evidence_certificates = db.Column(db.String(20))  # 'all', 'some', 'none'
    evidence_cv_mention = db.Column(db.String(20))  # 'both', 'cv', 'application', 'none'
    
    def __repr__(self):
        return f'<Assessment {self.worker.full_name} - {self.compliance_status}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'worker_id': self.worker_id,
            'assessment_date': self.assessment_date.isoformat() if self.assessment_date else None,
            'compliance_status': self.compliance_status,
            'risk_score': self.risk_score,
            'assessment_outcome': self.assessment_outcome,
            'recommendations': self.recommendations,
            'assessed_by': self.assessed_by,
            'ai_confidence_score': self.ai_confidence_score,
            'evidence_certificates': self.evidence_certificates,
            'evidence_cv_mention': self.evidence_cv_mention
        }

class QualificationTemplate(db.Model):
    """Model for predefined qualification templates"""
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(500), nullable=False)
    level = db.Column(db.String(50))
    category = db.Column(db.String(100))  # 'healthcare', 'education', etc.
    soc_codes = db.Column(db.Text)  # JSON string of applicable SOC codes
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<QualificationTemplate {self.title}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'level': self.level,
            'category': self.category,
            'soc_codes': self.soc_codes,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Keep the original User model for authentication if needed
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email
        }

