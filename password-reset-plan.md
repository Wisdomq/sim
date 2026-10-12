# Password Reset Workflow - Implementation Plan

## Critical Security Gap Identified

**Current State:** No password reset functionality exists. If users forget their passwords, they have no way to recover access to their accounts.

**Impact:** Critical - users can be permanently locked out of their accounts, requiring manual intervention by administrators.

## Required Implementation

### Backend Changes (Required)

#### 1. Database Schema Changes
**New Table: `PasswordResetToken`**
```sql
CREATE TABLE password_reset_tokens (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    token VARCHAR(255) UNIQUE NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    used_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    dealer_id INTEGER NOT NULL,
    INDEX idx_token (token),
    INDEX idx_user_id (user_id),
    INDEX idx_expires_at (expires_at)
);
```

**Rationale:** Store password reset tokens with expiration times to enable secure password recovery workflow.

#### 2. Backend API Endpoints

**POST /api/v1/auth/forgot-password**
- Input: `{"email": "user@example.com"}`
- Logic:
  1. Find user by email
  2. Generate secure random token
  3. Store token in `password_reset_tokens` table
  4. Send email with reset link containing token
  5. Return success (always return success to prevent email enumeration)
- Output: `{"message": "If the email exists, a reset link has been sent"}`

**POST /api/v1/auth/reset-password**
- Input: `{"token": "secure_token", "new_password": "new_secure_password"}`
- Logic:
  1. Validate token exists and is not expired
  2. Validate token has not been used
  3. Update user password hash
  4. Mark token as used
  5. Return success
- Output: `{"message": "Password has been reset successfully"}`

**POST /api/v1/auth/validate-reset-token**
- Input: `{"token": "secure_token"}`
- Logic:
  1. Validate token exists and is not expired
  2. Validate token has not been used
  3. Return token validity
- Output: `{"valid": true/false, "expires_at": "timestamp"}`

#### 3. Email Service
**New Configuration in `settings.py`:**
```python
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")
SMTP_FROM = os.getenv("SMTP_FROM", "noreply@simcards.com")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
```

**New Email Template:**
```
Subject: Reset Your SIM Cards Password

Hello {user_name},

You requested a password reset for your SIM Cards account.

Click the link below to reset your password:
{frontend_url}/reset-password?token={token}

This link will expire in 1 hour.

If you did not request this password reset, please ignore this email.

Best regards,
SIM Cards Team
```

#### 4. Security Considerations
- Token expiration: 1 hour
- Token length: 32+ characters random string
- Rate limiting: 3 requests per hour per email
- Password strength validation
- Invalidate all user sessions after password reset
- Log all password reset attempts

### Frontend Changes

#### 1. Web App (HQ Only)

**New Page: `/forgot-password`**
- Email input field
- Submit button
- Success message after submission
- Link back to login page

**New Page: `/reset-password`**
- Token validation from URL parameter
- New password input field
- Confirm password input field
- Password strength indicator
- Submit button
- Success/error messages
- Redirect to login after success

**Login Page Enhancement**
- Add "Forgot Password?" link below password field
- Link to `/forgot-password` page

#### 2. Mobile App (All Roles)

**New Screen: Forgot Password**
- Email input field
- Submit button
- Loading state during submission
- Success message with instructions
- Back to login button

**New Screen: Reset Password**
- Auto-detect token from deep link
- New password input field
- Confirm password input field
- Password strength indicator
- Submit button
- Success/error messages
- Auto-redirect to login after success

**Login Screen Enhancement**
- Add "Forgot Password?" link below password field
- Navigate to Forgot Password screen

#### 3. Deep Linking (Mobile)
**Configure App Links:**
- Handle links like `simcards://reset-password?token=xxx`
- Parse token and navigate to Reset Password screen
- Handle invalid/expired tokens gracefully

## Implementation Phases

### Phase 1: Backend Foundation (Critical)
1. Create database migration for `password_reset_tokens` table
2. Add email service configuration
3. Implement email sending functionality
4. Create password reset token generation/validation logic
5. Add backend API endpoints
6. Add rate limiting
7. Add logging

**Estimated Time:** 3-4 hours
**Database Changes:** Required (1 new table)

### Phase 2: Web Frontend (Critical)
1. Create `/forgot-password` page
2. Create `/reset-password` page
3. Add "Forgot Password?" link to login page
4. Implement form validation
5. Add password strength indicator
6. Add success/error handling
7. Test email delivery flow

**Estimated Time:** 2-3 hours
**Database Changes:** None

### Phase 3: Mobile Frontend (Critical)
1. Create Forgot Password screen
2. Create Reset Password screen
3. Add "Forgot Password?" link to login screens
4. Implement deep link handling
5. Add password strength indicator
6. Add success/error handling
7. Test on emulator

**Estimated Time:** 2-3 hours
**Database Changes:** None

### Phase 4: Testing & Security Review (Critical)
1. Unit tests for token generation/validation
2. Integration tests for API endpoints
3. Email delivery testing
4. Security audit (token strength, expiration, rate limiting)
5. User acceptance testing
6. Documentation updates

**Estimated Time:** 2-3 hours
**Database Changes:** None

## Security Requirements

### Password Policy
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character
- Cannot reuse last 3 passwords (optional enhancement)

### Token Security
- Cryptographically secure random token generation
- 1-hour expiration
- Single-use only
- Invalidated after password change
- Rate limiting to prevent abuse

### Email Security
- TLS/SSL for SMTP connections
- No sensitive data in email content
- Generic success messages to prevent email enumeration
- Logging of all reset attempts

## Environment Variables Required

```bash
# Email Configuration
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=noreply@simcards.com

# Frontend URL for reset links
FRONTEND_URL=http://localhost:3000  # or production URL
```

## Testing Strategy

### Unit Tests
- Token generation uniqueness
- Token expiration validation
- Token usage validation
- Password strength validation
- Rate limiting logic

### Integration Tests
- Forgot password API endpoint
- Reset password API endpoint
- Token validation endpoint
- Email delivery simulation
- Error handling scenarios

### Security Tests
- Token expiration enforcement
- Rate limiting enforcement
- Password policy enforcement
- Session invalidation after reset
- Email enumeration prevention

### User Acceptance Tests
- Complete forgot password flow
- Complete reset password flow
- Invalid token handling
- Expired token handling
- Mobile deep link handling

## Rollback Plan

If issues arise:
1. Disable password reset endpoints via feature flag
2. Remove new routes from frontend
3. Keep database table (harmless if unused)
4. Revert email configuration changes

## Success Criteria

1. Users can successfully request password reset via email
2. Users can successfully reset password using email link
3. Invalid/expired tokens are properly rejected
4. Rate limiting prevents abuse
5. All sessions are invalidated after password reset
6. Email delivery works reliably
7. Mobile deep links work correctly
8. Security requirements are met

## Timeline Estimate

**Total Implementation Time:** 9-13 hours
- Phase 1 (Backend): 3-4 hours
- Phase 2 (Web): 2-3 hours  
- Phase 3 (Mobile): 2-3 hours
- Phase 4 (Testing): 2-3 hours

## Dependencies

**Required:**
- SMTP email service (Gmail, SendGrid, AWS SES, etc.)
- Email credentials
- Frontend URL for reset links

**Optional:**
- Email template service (for better formatting)
- SMS fallback (for users without email)
- Multi-factor authentication enhancement

## Risk Assessment

**High Risk:**
- Email delivery failures
- Email spam filtering
- SMTP configuration issues

**Medium Risk:**
- Deep link configuration issues
- Token expiration edge cases
- Rate limiting false positives

**Low Risk:**
- UI/UX issues
- Mobile compatibility
- Browser compatibility

## Recommendation

**Proceed with implementation** as this is a critical security feature. The database change is minimal (1 new table) and well-contained. The implementation follows industry best practices for password reset workflows.

**Priority:** Critical - should be implemented before production deployment.