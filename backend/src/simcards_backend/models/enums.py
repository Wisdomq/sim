"""Shared enum values used by the domain model and API schemas."""

from enum import Enum


class Role(str, Enum):
    HQ = "HQ"
    BRANCH = "BRANCH"
    BA = "BA"


class AccountStatus(str, Enum):
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    FLAGGED_INACTIVE = "FLAGGED_INACTIVE"


class BranchType(str, Enum):
    VAN = "VAN"
    SHOP = "SHOP"
    INDIVIDUAL = "INDIVIDUAL"


class PeriodType(str, Enum):
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"


class SubjectType(str, Enum):
    BA = "BA"
    BRANCH = "BRANCH"
    DEALER = "DEALER"


class AccountFlagType(str, Enum):
    INACTIVE_3_DAYS = "INACTIVE_3_DAYS"


class StockBatchSource(str, Enum):
    PDF_IMPORT = "PDF_IMPORT"
    BOX_SCAN = "BOX_SCAN"


class SimStatus(str, Enum):
    IN_HQ_STOCK = "IN_HQ_STOCK"
    WITH_BRANCH = "WITH_BRANCH"
    WITH_BA = "WITH_BA"
    SOLD = "SOLD"
    RETURNED_TO_BRANCH = "RETURNED_TO_BRANCH"
    RETURNED_TO_HQ = "RETURNED_TO_HQ"
    EXPIRED = "EXPIRED"


class OwnerType(str, Enum):
    HQ = "HQ"
    BRANCH = "BRANCH"
    BA = "BA"


class TransferType(str, Enum):
    DISTRIBUTION = "DISTRIBUTION"
    REASSIGNMENT = "REASSIGNMENT"
    RETURN = "RETURN"


class ScannedVia(str, Enum):
    CAMERA = "CAMERA"


class ReturnStatus(str, Enum):
    REQUESTED = "REQUESTED"
    COMPLETED = "COMPLETED"


class SafaricomImportStatus(str, Enum):
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class ReconciliationMatchStatus(str, Enum):
    MATCHED = "MATCHED"
    SOLD_NOT_ACTIVATED = "SOLD_NOT_ACTIVATED"
    ACTIVATED_NOT_RECORDED_SOLD = "ACTIVATED_NOT_RECORDED_SOLD"


class NotificationType(str, Enum):
    ACCOUNT_FLAGGED_INACTIVE = "ACCOUNT_FLAGGED_INACTIVE"
