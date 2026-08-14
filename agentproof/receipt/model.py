"""Compatibility exports for the single official AgentProof receipt model."""

from ..models import ClaimResult as Claim
from ..models import VerificationReceipt as Receipt

__all__ = ["Claim", "Receipt"]
