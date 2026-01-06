"""
License services for PaaS deployments
"""
from app.services.license.license_activation_service import LicenseActivationService
from app.services.license.server_fingerprint import ServerFingerprint

__all__ = ["LicenseActivationService", "ServerFingerprint"]

