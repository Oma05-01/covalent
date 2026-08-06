# Covalent Master Test Tracker

## Phase A — Identity & Foundation
**Goal:** Users can securely join the platform, wallets are provisioned, and risk profiles are initialized.

### Unit Tests
- [*] `test_user_creation`: Validates user is created with correct defaults.
- [*] `test_password_hashing`: Ensures raw passwords are not stored in the DB.
- [*] `test_public_id_generation`: Confirms `CVL-XXXXX` format and uniqueness on save.
- [*] `test_trust_score_initialization`: Checks default starts at 100.
- [*] `test_fraud_risk_initialization`: Checks default starts at 0.0.
- [*] `test_wallet_creation_signal`: Asserts a Wallet is automatically created when a User is created.
- [*] `test_jwt_generation`: Verifies valid tokens are generated for active users.
- [*] `test_permission_classes`: Validates `IsLawyer`, `IsVendor`, `IsBuyer` logic.

### Integration Tests
- [*] `test_registration_pipeline`: 
    - Asserts User creation.
    - Asserts Wallet creation with `0.00` balances.
    - Asserts Notification Preferences creation.
- [*] `test_login_flow`: Asserts login returns a valid JWT access and refresh token.
- [*] `test_token_refresh`: Asserts the refresh token correctly issues a new access token.

### Business Rule Tests
- [*] `test_duplicate_email_registration`: Asserts same email cannot register twice (returns 400).
- [*] `test_duplicate_nin_registration`: Asserts same NIN cannot be reused across accounts.
- [*] `test_lawyer_role_isolation`: Asserts Lawyer role receives 403 on Freelancer/Vendor endpoints.
- [*] `test_unverified_user_restrictions`: Asserts `is_kyc_verified=False` cannot create contracts.

### End-to-End (E2E) Tests
- [*] `test_e2e_onboarding_flow`:
    1. Client registers account.
    2. Client logs in (receives JWT).
    3. Client completes KYC payload.
    4. Client views Dashboard (fetches wallet & public ID).
    5. Client logs out (blacklists token).
    6. Client logs in again successfully.


Phase 2 — Contract Engine Test Tracker
1. Models & Database Integrity
File: accounts/tests/tests_models.py

[x] test_contract_auto_calculates_escrow

[x] test_direct_contract_overrides_public_flag

[x] test_open_market_contract_creation

[x] test_cannot_create_direct_without_counterparty

[x] test_contract_application_creation 

[x] test_duplicate_application_blocked 

2. Business Logic & Versioning (Next Up)
File: accounts/tests/tests_services.py
This file will handle the state machine logic and immutability.

[x] test_contract_version_snapshot_created 

[x] test_cannot_edit_accepted_contract

[x] test_acceptance_timestamp_recorded

[x] test_plain_language_summary_generation

3. API Integration & Routing
File: accounts/tests/tests_api.py (or tests_views.py)
This file will test the Django REST Framework endpoints and permissions.

[x] test_direct_proposal_flow

[x] test_open_market_bidding_flow

[x] test_contract_acceptance_binds_vendor

[x] test_contract_rejection_flow

4. End-to-End (E2E) Flow
File: accounts/tests/tests_e2e.py
Simulates the full user journey through the platform.

[X] test_e2e_direct_contract_lifecycle

[X] test_e2e_marketplace_lifecycle

## Phase 3 — Escrow, Ledger & Arbitration Subsystem
**Goal:** Guarantee atomic financial transactions, prevent double-spending, strictly track fund movements via a ledger, and route disputes to the decentralized legal consensus engine.

### 1. Financial Services & Ledger Integrity 
**File:** `escrow/tests/tests_wallet.py` (or `accounts/tests/tests_wallet.py`)
- [X] `test_deposit_and_ledger_entry`: Asserts deposits increase `available_balance` and write to `LedgerTransaction`.
- [X] `test_withdraw_funds_and_limits`: Asserts withdrawals debit `available_balance` and strictly prevent overdrafts.
- [X] `test_lock_funds_in_escrow`: Asserts `lock_escrow` safely moves funds from available to `locked_escrow_balance`.
- [X] `test_cannot_withdraw_locked_funds`: Asserts locked funds are mathematically fenced off from user withdrawal attempts.
- [X] `test_escrow_never_negative`: Asserts the engine prevents locking more funds than the user actually holds.
- [X] `test_release_escrow_to_vendor`: Asserts `release_escrow` simultaneously deducts from buyer's lock, credits vendor's available balance, and logs both ledger entries atomically.

### 2. API Integration & Webhooks
**File:** `escrow/tests/tests_api.py`
- [X] `test_paystack_webhook_funds_and_locks_escrow`: Asserts the `/verify-payment/` endpoint intercepts the webhook, funds the buyer, and instantly locks the escrow.
- [X] `test_buyer_approval_releases_escrow_to_vendor`: Asserts hitting the `approve` contract action releases funds and sets contract status to `RELEASED`.
- [X] `test_vendor_delivery_starts_timer`: Asserts vendor marking item as `deliver` sets `delivered_at` and calculates the `auto_release_at` deadline.
- [X] `test_raise_dispute_deducts_fee`: Asserts initiating a dispute debits the arbitration fee using the ledger service before drafting lawyers.
- [X] `test_raise_dispute_drafts_lawyers`: Asserts dispute creation successfully drafts 3 eligible, non-involved lawyers.
- [X] `test_lawyer_vote_triggers_consensus`: Asserts casting the 3rd valid verdict automatically executes `execute_dispute_consensus` and pays out the winner.
- [X] `test_raise_dispute_deducts_fee_and_drafts_lawyers`
Verifies: Raising a dispute correctly debits the arbitration fee through the ledger service, transitions the contract status, and automatically drafts 3 active lawyers in good standing.

### 3. End-to-End (E2E) Flow
**File:** `escrow/tests/tests_e2e.py`
- [X] `test_e2e_happy_path_escrow`:
    1. Buyer funds contract via Paystack.
    2. Vendor dispatches and delivers item.
    3. Buyer approves item within inspection window.
    4. Vendor successfully withdraws available balance.
- [X] `test_e2e_dispute_and_arbitration_flow`:
    1. Buyer funds and Vendor delivers.
    2. Buyer rejects item at the door (triggers Dispute).
    3. Buyer is charged arbitration fee, Vendor trust score drops.
    4. 3 Lawyers accept draft and vote (2 for Vendor, 1 for Buyer).
    5. Vendor is awarded escrow, Buyer is penalized, Lawyers receive cuts.


# Phase 4: Delivery & Completion — Test Suite Documentation

This document outlines the test specifications, business rules, and verification procedures implemented for **Phase 4 (Delivery & Completion)** of the Covalent escrow and wallet subsystem.

---

## 1. Overview & Objectives
Phase 4 bridges active contract work and final payout by introducing:
*   **Time-Bound Inspection Windows**: Automated countdown timers governing client review periods.
*   **Contract Immutability**: Restrictions preventing modification of core contract parameters post-delivery.
*   **Automated Background Processing**: Scheduler rules ensuring auto-release mechanisms only trigger after inspection windows expire.
*   **End-to-End Lifecycle Flow**: Complete verification from vendor delivery, inspection, client approval, to final fund release.

---

## 2. Test Suites Breakdown

### A. Unit Tests (`escrow/tests/tests_delivery.py`)
Validates core service logic, model state transitions, and time calculations.

*   **`test_delivery_status_changes`**
    *   *Description:* Verifies that marking a funded contract as delivered correctly updates its status to `"DELIVERED"` and populates the `delivered_at` timestamp.
*   **`test_timer_calculations`**
    *   *Description:* Asserts that the `auto_release_at` deadline is accurately computed based on the configured inspection period hours (e.g., 48 or 72 hours).
*   **`test_delivered_contracts_immutable_terms`**
    *   *Description:* Ensures that critical financial parameters (such as `item_amount`) cannot be altered once a contract has entered the delivered state.

### B. Integration & Scheduler Tests (`escrow/tests/tests_delivery_integration.py`)
Validates API endpoints and background scheduler filtering logic.

*   **`test_vendor_marks_delivered_and_countdown_starts`**
    *   *Description:* Tests the authorized vendor POST endpoint (`/api/v1/escrow/contracts/{id}/deliver/`) to ensure it successfully initiates the countdown timer.
*   **`test_auto_release_only_after_timer`**
    *   *Description:* Business rule validation ensuring that automated background queries correctly ignore delivered contracts whose review windows are still active.

### C. End-to-End Tests (`escrow/tests/tests_delivery_e2e.py`)
Validates the complete user workflow from dispatch to settlement.

*   **`test_e2e_delivery_to_funds_release`**
    *   *Description:* Simulates the full transaction lifecycle:
        1. Vendor marks work as delivered.
        2. System initializes the inspection window countdown.
        3. Client reviews and approves work within the window.
        4. Contract transitions to `"RELEASED"` and escrow funds transfer directly to the vendor's available balance.


# Phase 5 — Dispute Resolution

**Goal:** Conflict resolution is fair, anonymous, and strictly adheres to the decentralized arbitration protocols.

### Unit Tests
- [x] **7-to-30-day timer respected:** Ensures disputes can only be raised within the valid timeframe.
- [x] **Evidence scrubbed for anonymity:** Verifies that uploaded files (`DisputeEvidence`) are passed through the `media_scrubber` to strip metadata before saving.
- [x] **Fee calculations:** Confirms the ₦5000 non-refundable support fee is correctly calculated and applied.

### Integration Tests
- [x] **Lawyers and parties are anonymous:** Validates that the API correctly masks the identities of the buyer and vendor (e.g., as "Party A" and "Party B") when serving data to the assigned lawyers.
- [x] **Raise dispute deducts support fee and locks state:** Ensures that initiating a dispute successfully transitions the contract state to `DISPUTED` and deducts the required operational fee.

### E2E Test
- [x] **Full Dispute Lifecycle:** Simulates the complete end-to-end flow:
  1. Dispute Raised (Timer & Fee Validation)
  2. Evidence Uploaded (Anonymization Triggered)
  3. Arbitrators Assigned & Accepted
  4. Voting Consensus Reached (Minimum 80-character justification enforced)
  5. Payout & Contract State Transited (`REFUNDED` or `RELEASED`)


# Phase 6 — Trust & Governance

**Goal:** Accountability is enforced across the platform through automated scoring, penalties, and progressive restrictions.

### Unit Tests
- [X] **Trust Score changes:** Verify exact mathematical adjustments to a user's trust rating.
- [X] **Loyalty points:** Ensure successful transactions accurately accrue loyalty points.
- [X] **Penalty engine:** Validate the point deduction logic for infractions.
- [X] **Warning engine:** Confirm that dropping below specific thresholds triggers the correct account flags.

### Integration Tests
- [X] **Dispute affects trust:** Ensure losing a dispute automatically triggers the penalty engine.
- [X] **Clean contracts improve trust:** Verify that completing contracts without disputes integrates with the trust score increment logic.
- [X] **Loyalty updates:** Confirm database state changes when loyalty tiers are crossed.

### E2E Test
- [X] **The "Bad Actor" Pipeline:**
      Repeated bad behavior ➔ Warning ➔ Restriction ➔ Suspension.

### Business Rule Tests
- [X] **Trust boundaries:** Trust score never exceeds maximum or drops below minimum bounds.
- [X] **Consistent penalties:** Ensure specific violations carry exact, predictable penalty weights.
- [X] **Recovery rules:** Validate the conditions under which a restricted user can recover their standing.
- [X] **Hidden fraud score:** Ensure the internal fraud risk score remains entirely unaffected by public-facing actions or user manipulations.


## Phase 7 — Fraud Detection
**Goal:** Stop abuse early.

### Unit Tests
- [x] Pattern detection (Analyzes dispute ratios and rapid contract creation)
- [x] Device matching (Hashes IP and User-Agent)
- [x] Risk scoring (Evaluates telemetry vectors and historical patterns)

### Integration Tests
- [x] Multiple suspicious contracts (+25 risk penalty)
- [x] Fake dispute patterns (+30 to +60 risk penalty)
- [x] Repeat account detection (Ban evasion via shared device footprint)

### E2E Test
- [x] Create suspicious behavior -> Fraud score increases -> Restrictions applied

### Business Rule Tests
- [x] False positives reviewed (Manual admin override logic)
- [x] Fraud score remains private (Not exposed in public API serialzers)
- [x] Restrictions proportional to risk (70=Restricted, 100=Suspended)

## Phase 8: AI Contract Engine Integrity
**Focus:** Validation of AI-generated contract components, state machine transitions, and business rule enforcement.

* **AI Generation & Human-in-the-Loop:** Verified that backend business rules strictly gate the "Save, Patch, and Pay" flow. Tests confirm that user edits are safely incorporated without bypassing platform validation, neutralizing potential prompt injection vectors.
* **Contract State Transitions:** Unit and integration tests validate the critical sequence of contract states (e.g., PROPOSED → FUNDED → RELEASED).
* **System Integrity:** Verified that core platform modules interact cleanly with the AI generation outputs without breaking existing API schemas.

Phase 9: Governance & Admin Access Control
Focus: Strict Role-Based Access Control (RBAC) and immutable system logging.

RBAC Enforcement (accounts/tests/test_admin_permissions.py):

test_base_admin_blocks_inactive_and_regular_users: Ensures standard platform users and deactivated staff are strictly locked out of back-office endpoints.

test_is_super_admin_blocks_lower_tiers: Validates that Tier-1 and Dispute managers cannot access highly privileged Super Admin endpoints.

test_is_risk_officer_allows_super_admin_but_blocks_dispute_manager: Confirms role inheritance (Super Admins can execute Risk Officer duties) while preventing horizontal role escalation (Dispute Managers cannot access Risk endpoints).

Immutable Audit Ledger (audit/tests/test_audit_logger.py):

test_log_admin_action_creates_record: Proves the AuditLogger service accurately captures exact state-change payloads and generic model relationships.

test_admin_audit_log_is_immutable: Validates the save() method override, proving that the database rejects any attempt to update or alter an existing audit log, ensuring cryptographic-level operational trust.

Admin Dashboard & Discovery (accounts/tests/test_admin_dashboard.py):

test_admin_can_list_users_with_pagination: Ensures backend stability by enforcing paginated list responses, preventing memory overloads when querying the entire user database.

test_admin_can_search_by_email & test_admin_can_filter_suspended_users: Validates DRF filter integrations, proving Risk Officers can instantly isolate accounts by partial text search or account state (e.g., active vs. suspended).

test_non_admins_are_blocked: Guarantees that internal dashboard data (like exact timestamps and trust scores) remains completely inaccessible to standard VENDOR or BUYER accounts.

Governance End-to-End Workflow (accounts/tests/test_admin_e2e.py & accounts/tests/test_admin_integration.py):

test_e2e_admin_investigates_and_penalizes_user: Simulates the complete circuit-breaker lifecycle—an admin searches for a reported user, identifies the target, applies a suspension penalty, and verifies the automated creation of the audit trail.

test_risk_officer_can_suspend_user_and_creates_audit_log: Verifies that applying a penalty successfully toggles the target's is_active state to False and logs the exact Admin ID and state change payload.

test_suspend_fails_without_justification: Ensures strict compliance by rejecting any administrative account suspensions that do not include a written justification payload.