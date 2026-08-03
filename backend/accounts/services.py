from django.core.exceptions import ValidationError
from django.utils import timezone
from .models import ContractVersion

def update_contract_terms(contract, user, **kwargs):
    """
    Updates contract terms and safely stamps an immutable version.
    """
    # 1. Enforce Business Rule: No edits if accepted
    if contract.status not in ["DRAFT", "PROPOSED", "OPEN"]:
        raise ValidationError("Cannot edit an accepted or active contract.")
    
    # 2. Update the contract fields dynamically
    for field, value in kwargs.items():
        if hasattr(contract, field):
            setattr(contract, field, value)
    
    # Needs to be saved to calculate total_escrow and clean data
    contract.full_clean() 
    contract.save()

    # 3. Create the immutable snapshot (Versioning)
    last_version = contract.versions.first() # Meta ordering is '-version_number'
    new_version_num = (last_version.version_number + 1) if last_version else 1
    
    ContractVersion.objects.create(
        contract=contract,
        version_number=new_version_num,
        item_title=contract.item_title,
        item_description=contract.item_description,
        item_amount=contract.item_amount,
        delivery_fee=contract.delivery_fee,
        plain_language_summary=contract.plain_language_summary or "",
        created_by=user
    )
    
    return contract


def accept_contract(contract, vendor):
    """
    Binds a vendor to a contract and locks the state.
    """
    contract.vendor = vendor
    contract.is_public = False
    contract.status = "AWAITING_FUNDING"
    contract.accepted_at = timezone.now()
    
    contract.full_clean()
    contract.save()
    return contract


def generate_contract_summary(contract):
    """
    Generates a plain-language summary of the legal obligations.
    (This is a placeholder template that you can swap with an LLM integration later).
    """
    summary = (
        f"This is an agreement for '{contract.item_title}'. "
        f"The total escrow amount to be locked is ₦{contract.total_escrow}, "
        f"which includes a delivery fee of ₦{contract.delivery_fee}."
    )
    contract.plain_language_summary = summary
    contract.save()
    
    return contract