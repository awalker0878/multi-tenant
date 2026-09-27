"""Scoped, independently authenticated control-plane authorization."""

from .model import (ApprovalSnapshot, AuthorizedPlan, FrozenPlan, PlanApproval,
                    PlanScope, PortfolioScope, RoleGrant, VerifiedPrincipal,
                    WorkerGrant)
from .service import (AuthorityDenied, AuthorityService, AuthenticationFailed,
                      require_scoped_role, require_workload_role)

__all__ = ('ApprovalSnapshot', 'AuthorizedPlan', 'FrozenPlan', 'PlanApproval',
           'PlanScope', 'PortfolioScope', 'RoleGrant', 'VerifiedPrincipal', 'WorkerGrant',
           'AuthorityDenied', 'AuthorityService', 'AuthenticationFailed',
           'require_scoped_role', 'require_workload_role')
