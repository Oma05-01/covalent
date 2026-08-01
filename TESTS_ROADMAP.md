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
- [ ] `test_e2e_onboarding_flow`:
    1. Client registers account.
    2. Client logs in (receives JWT).
    3. Client completes KYC payload.
    4. Client views Dashboard (fetches wallet & public ID).
    5. Client logs out (blacklists token).
    6. Client logs in again successfully.