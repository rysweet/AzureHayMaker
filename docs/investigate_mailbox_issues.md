# Mailbox Investigation - Three Root Causes

## Issue 1: Cloud-only users not getting mailboxes
- Created: testcloudmailbox user
- License: E5 assigned
- OnPremisesSync: null (cloud-only)
- Result: Still no mailbox after 60s
- Question: Why? License should auto-create mailbox

## Issue 2: Admin consent failing
- Command: az ad app permission grant --id ... --api ...
- Error: "requires --scope parameter"
- Result: Permission NOT actually granted
- Question: What's the correct command syntax?

## Issue 3: Two different errors
- MailboxNotEnabledForRESTAPI: Mailbox doesn't exist yet
- ErrorAccessDenied: Permission issue OR mailbox exists but no access
- Question: Which error means what exactly?

## Investigation Plan
1. Fix admin consent command (find correct --scope syntax)
2. Check if ANY mailbox exists in tenant (find one working example)
3. Try creating user via different method (New-Mailbox equivalent)
4. Check Exchange Online organization settings
