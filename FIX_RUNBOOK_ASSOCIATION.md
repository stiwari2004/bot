# Fix: Runbook Association with Tickets

## Problem
1. When viewing ticket details, matched runbooks weren't showing
2. When generating a runbook, it wasn't being associated with the ticket
3. The flow was broken after removing the `checkForExistingRunbook()` function

## Root Causes

### 1. Backend Only Searched for Classified Tickets
The backend endpoint `/api/v1/tickets/demo/tickets/{ticket_id}` only returned matched runbooks if:
- `ticket.classification` exists AND
- `ticket.classification != "false_positive"`

**Fix:** Changed to always search unless explicitly "false_positive"

### 2. Runbook Generation Didn't Associate with Ticket
The runbook generation endpoint didn't:
- Accept `ticket_id` parameter
- Store the generated runbook in `ticket.meta_data.matched_runbooks`

**Fix:** Added `ticket_id` parameter and association logic

## Changes Made

### Backend: `backend/app/api/v1/endpoints/ticket_ingestion.py`
1. **Always perform semantic search** (unless ticket is "false_positive")
2. **Check `ticket.meta_data.matched_runbooks`** for previously stored runbooks
3. **Combine both sources** (stored + semantic search)

### Backend: `backend/app/api/v1/endpoints/runbooks.py`
1. **Added `ticket_id` parameter** to `/demo/generate-agent` endpoint
2. **After generation, associate runbook with ticket:**
   - Add runbook to `ticket.meta_data.matched_runbooks`
   - Store with confidence_score=1.0 (perfect match)
   - Commit changes to database

### Frontend: `frontend-nextjs/src/components/Tickets.tsx`
1. **Removed `checkForExistingRunbook()` function** (was causing 409 errors)
2. **Added `ticket_id` to runbook generation request**
3. **Ticket detail refresh** already handled in `onClose` callback

## Flow Now

### Viewing Ticket Details
1. Frontend calls `/api/v1/tickets/demo/tickets/{ticket_id}`
2. Backend:
   - Checks `ticket.meta_data.matched_runbooks` for stored runbooks
   - Performs semantic search (unless false_positive)
   - Combines both sources
   - Returns `matched_runbooks` array
3. Frontend displays matched runbooks with "Execute Runbook" button

### Generating Runbook
1. User clicks "Generate New Runbook" in ticket detail modal
2. Frontend calls `/api/v1/runbooks/demo/generate-agent?ticket_id={ticket_id}&...`
3. Backend:
   - Generates runbook
   - Associates runbook with ticket (updates `ticket.meta_data.matched_runbooks`)
   - Returns runbook
4. Frontend shows generated runbook
5. When modal closes, ticket detail is refreshed, showing the new runbook

## Testing

1. **View ticket 31:**
   - Should show runbook ID 5 if it exists and is active
   - Should show semantic search results

2. **Generate new runbook:**
   - Should associate with ticket
   - Should appear in matched runbooks after modal closes

3. **Execute runbook:**
   - Should work from matched runbooks list

## Next Steps

1. Restart backend: `docker-compose restart backend`
2. Refresh frontend page
3. Test viewing ticket 31 - should show matched runbooks
4. Test generating new runbook - should associate with ticket




