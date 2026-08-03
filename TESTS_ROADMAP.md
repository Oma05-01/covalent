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

---

## 3. Test Execution Command

To run the complete Phase 4 test suite, execute the following command from your backend root directory: