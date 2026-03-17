"""
Provisioning Controller — infrastructure provisioning across cloud providers
"""
from sqlalchemy.orm import Session

from app.controllers.provisioning_provision_mixin import ProvisioningProvisionMixin
from app.controllers.provisioning_projects_mixin import ProvisioningProjectsMixin
from app.controllers.provisioning_templates_mixin import ProvisioningTemplatesMixin


class ProvisioningController(ProvisioningProvisionMixin, ProvisioningProjectsMixin, ProvisioningTemplatesMixin):
    def __init__(self, db: Session, tenant_id: int, user_id: int = None):
        self.db = db
        self.tenant_id = tenant_id
        self.user_id = user_id


def get_provisioning_controller(db: Session, tenant_id: int, user_id: int = None) -> ProvisioningController:
    return ProvisioningController(db, tenant_id, user_id)
