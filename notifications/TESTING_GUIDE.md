# Notifications System - Testing & Validation Guide

This guide covers manual testing, automated test execution, and validation of the complete notifications system.

## Quick Start: Running Automated Tests

### Run all notification tests:
```bash
python manage.py test notifications
```

### Run specific test class:
```bash
python manage.py test notifications.tests.NotificationSignalHandlerTests
python manage.py test notifications.tests.NotificationServiceTests
python manage.py test notifications.tests.NotificationCleanupTests
python manage.py test notifications.tests.NotificationIntegrationTests
```

### Run with verbose output:
```bash
python manage.py test notifications -v 2
```

### Run with coverage report (if coverage.py is installed):
```bash
coverage run --source='notifications' manage.py test notifications
coverage report
coverage html  # Generate HTML report in htmlcov/
```

---

## Manual Testing Workflow

### 1. Test User Notification Triggers

#### 1.1 Test New User Registration Notification
**Expected Behavior:** User sees "Welcome to GamiKonnect!" notification upon registration.

**Steps:**
1. Register a new user account at `/accounts/signup/`
2. After registration, log in to the gamer dashboard at `/dashboard/`
3. Look for notification bell icon in top nav (should show badge with count=1)
4. Click the bell icon to open dropdown
5. Verify notification shows:
   - Title: "Welcome to GamiKonnect!"
   - Category: "general"
   - Message includes user's name

**Verification:**
- [ ] Notification appears in bell icon dropdown within 3 seconds
- [ ] Notification appears in unread list
- [ ] Notification center shows the notification

---

#### 1.2 Test Profile Completion Notification
**Expected Behavior:** User receives "Profile Complete!" notification after completing profile.

**Steps:**
1. Log in to an incomplete profile (profile_completed=False)
2. Complete the profile by filling in bio, location, preferences
3. Submit the profile completion form
4. Dismiss any modal/message
5. Check notification bell

**Verification:**
- [ ] "Profile Complete!" notification appears immediately
- [ ] Notification appears in dashboard notification dropdown
- [ ] Notification is marked as unread until clicked

---

#### 1.3 Test Level-Up Notification
**Expected Behavior:** Player receives "Level Up!" notification when reaching new level.

**Steps:**
1. Create a test competition where gamer can earn points/win
2. Play and win the competition to earn points
3. Accumulate points until reaching the next level threshold
4. System auto-detects level-up and creates notification
5. Check dashboard

**Verification:**
- [ ] "Level Up!" notification appears with level number
- [ ] Notification importance is set to "high"
- [ ] Notification shows in real-time on dashboard (WebSocket or polling)

---

#### 1.4 Test Achievement Unlock Notification
**Expected Behavior:** Player receives achievement unlock notification.

**Steps:**
1. Create/find an achievement with unlock criteria
2. Trigger the achievement (e.g., win first competition, reach level 5)
3. Check dashboard for notification
4. Check notification center

**Verification:**
- [ ] "Achievement Unlocked" notification appears with achievement name
- [ ] Notification shows achievement badge/icon if available
- [ ] Email is sent (check Django mail backend or email logs)

---

### 2. Test Dashboard Integration

#### 2.1 Test Notification Bell and Badge
**Expected Behavior:** Bell shows count of unread notifications.

**Steps:**
1. Log in to dashboard
2. Bell icon shows "0" if no unread notifications
3. Create a test notification via Django admin
4. Refresh page or use WebSocket connection
5. Bell icon updates to show new count
6. Click bell icon to open dropdown

**Verification:**
- [ ] Badge count increments with new notifications
- [ ] Badge displays "99+" if count exceeds 99
- [ ] Badge disappears when count is 0
- [ ] Dropdown shows 5 most recent notifications
- [ ] Dropdown shows "empty state" message when no notifications

---

#### 2.2 Test Notification Dropdown
**Expected Behavior:** Dropdown shows recent notifications with details.

**Steps:**
1. Create 3-5 test notifications via admin
2. Send them to the logged-in user
3. Open the dashboard
4. Click the notification bell
5. Examine the dropdown

**Verification:**
- [ ] Dropdown shows notifications in reverse chronological order (newest first)
- [ ] Each notification shows: title, message preview, category, time since created
- [ ] Unread notifications have different background color
- [ ] "View All" link goes to `/notifications/center/`
- [ ] Dropdown closes when clicking outside of it

---

#### 2.3 Test Mark as Read
**Expected Behavior:** Clicking notification marks it as read.

**Steps:**
1. From dashboard, open notification dropdown
2. Click on an unread notification
3. Check if badge count decreased
4. Check if notification is marked as read in notification center

**Verification:**
- [ ] Badge count updates immediately
- [ ] Notification background color changes (no longer highlighted)
- [ ] Notification center shows updated read status

---

### 3. Test Notification Center Page

#### 3.1 Test Pagination and Filtering
**Expected Behavior:** Full notification center shows all notifications with filtering.

**Steps:**
1. Go to `/notifications/center/`
2. Create 25+ notifications via admin
3. Check pagination (should show 20 per page)
4. Test category filter dropdown
5. Test read status filter

**Verification:**
- [ ] Notifications display in paginated list
- [ ] Category filter reduces results correctly
- [ ] Read status filter shows only read or unread
- [ ] Pagination controls work properly

---

#### 3.2 Test Mark All as Read
**Expected Behavior:** "Mark All as Read" button marks all notifications as read.

**Steps:**
1. Go to notification center
2. Create several unread notifications
3. Click "Mark All as Read" button
4. Verify all are marked as read
5. Go back to dashboard - badge count should be 0

**Verification:**
- [ ] All notifications show as read
- [ ] Badge on dashboard disappears
- [ ] Read timestamps are updated for all

---

### 4. Test Email Delivery

#### 4.1 Test Email Content
**Expected Behavior:** Notification emails are properly formatted HTML.

**Steps:**
1. Set Django mail backend to `django.core.mail.backends.locmem.EmailBackend` (or file backend)
2. Create and send a notification via admin
3. Check the email in `django.core.mail.outbox` (Python shell)

**Verification:**
- [ ] Email subject includes notification category and title
- [ ] Email contains HTML template with styling
- [ ] Email includes "View all notifications" and "Settings" links
- [ ] Email footer contains copyright and project name

---

#### 4.2 Test Email Merge Fields (if using template rendering)
**Expected Behavior:** Email templates render user/notification context variables.

**Steps:**
1. Create a template with {{username}}, {{title}}, {{category}}
2. Send notification with test user
3. Check email rendering

**Verification:**
- [ ] User name is correctly inserted
- [ ] Notification title is correct
- [ ] Category is correctly displayed

---

### 5. Test Real-Time Updates (WebSocket)

#### 5.1 Test WebSocket Connection
**Expected Behavior:** Dashboard connects to WebSocket for real-time updates.

**Steps:**
1. Open browser Developer Tools → Console
2. Go to dashboard
3. Look for logs indicating WebSocket connection
4. Create a notification while page is open
5. See notification appear without page refresh

**Verification:**
- [ ] No errors in browser console
- [ ] WebSocket connection established (check Network tab)
- [ ] Notification appears within 3 seconds of creation
- [ ] Badge count updates without page refresh

---

#### 5.2 Test WebSocket Fallback to Polling
**Expected Behavior:** If WebSocket fails, system falls back to polling.

**Steps:**
1. Open Developer Tools → Network
2. Block WebSocket connections (or disable on production)
3. Refresh dashboard
4. Check that polling starts (5-second interval)
5. Create notification and verify it appears

**Verification:**
- [ ] No WebSocket errors
- [ ] Polling requests appear in Network tab
- [ ] Notification appears after polling interval (within 5 seconds)

---

### 6. Test Notification Cleanup

#### 6.1 Test Manual Cleanup Command
**Expected Behavior:** Management command deletes expired notifications.

**Steps:**
1. Create notifications with past `expires_at` dates
2. Run: `python manage.py cleanup_expired_notifications`
3. Check if old notifications are deleted

**Verification:**
- [ ] Command runs without errors
- [ ] Expired notifications are deleted
- [ ] Non-expired notifications remain
- [ ] Recipient records are also deleted

---

#### 6.2 Test Scheduled Cleanup
**Expected Behavior:** Cleanup runs automatically daily at configured time.

**Steps:**
1. Check settings for `NOTIFICATION_CLEANUP_HOUR` (default: 2 AM)
2. Create a test notification with early expiry date
3. Wait for cleanup to run (or simulate with APScheduler)
4. Verify notification is deleted

**Verification:**
- [ ] Cleanup job appears in APScheduler job list
- [ ] Cleanup runs at configured time
- [ ] Expired notifications are removed daily

---

### 7. Test Different Notification Categories and Importance

#### 7.1 Create Notifications with Different Importance Levels
**Steps:**
1. Via Django admin, create notifications with:
   - Low importance → expires in ~7 days
   - Medium importance → expires in ~14 days
   - High importance → expires in ~30 days
   - Critical importance → expires in ~90 days
2. Check `expires_at` field for each

**Verification:**
- [ ] Low priority notifications expire quickly
- [ ] Critical notifications are preserved longer
- [ ] Expiry times align with importance levels

---

### 8. Test Admin Interface

#### 8.1 Test Admin List Display
**Expected Behavior:** Admin interface shows notifications with formatting.

**Steps:**
1. Go to `/admin/notifications/notification/`
2. Check list display shows:
   - Title with category icon/emoji
   - Importance as colored badge
   - Recipient count (linked to recipients)
   - Delivery status summary
   - Read rate percentage

**Verification:**
- [ ] All columns display correctly
- [ ] Filters work (category, importance, delivery_status)
- [ ] Search works on title and message
- [ ] Clicking recipient count shows recipients

---

#### 8.2 Test Admin Actions
**Expected Behavior:** Bulk actions for sending notifications.

**Steps:**
1. Check if bulk send action is available
2. Select notifications and send
3. Verify recipients are created

**Verification:**
- [ ] Bulk actions appear in admin
- [ ] Sending creates NotificationRecipient records

---

### 9. Test Edge Cases

#### 9.1 Test Empty Dropdown State
**Expected Behavior:** Dropdown shows helpful message when no notifications.

**Steps:**
1. Create a new user
2. Don't trigger any notifications
3. Go to dashboard
4. Click bell icon

**Verification:**
- [ ] Empty state message displays
- [ ] Bell icon has no badge
- [ ] "View All" link still works

---

#### 9.2 Test Very Long Notification Messages
**Expected Behavior:** Long messages are truncated in dropdown but full in center.

**Steps:**
1. Create notification with 500+ character message
2. Check dropdown (should truncate with ellipsis)
3. Check notification center (should show full message)

**Verification:**
- [ ] Dropdown shows truncated preview (~15 words)
- [ ] Notification center shows full message
- [ ] Layout isn't broken by long text

---

#### 9.3 Test Multiple Categories
**Expected Behavior:** Notifications display correct category and color.

**Steps:**
1. Create notifications for each category:
   - general, system, competition, payment, achievement, level, custom
2. Check display in dropdown and center

**Verification:**
- [ ] Categories display correctly
- [ ] Category badges have appropriate colors
- [ ] Category filters work

---

### 10. Performance & Load Testing

#### 10.1 Test with Large Number of Notifications
**Steps:**
1. Create 1000+ notifications for a user
2. Load notification center
3. Check page load time
4. Verify pagination handles large datasets

**Verification:**
- [ ] Page loads within 2 seconds
- [ ] Pagination works smoothly
- [ ] No SQL N+1 queries (check Django Debug Toolbar)

---

#### 10.2 Test Bulk Sending
**Steps:**
1. Send notification to 100+ users
2. Monitor database performance
3. Check if batching is effective

**Verification:**
- [ ] Bulk send completes within reasonable time
- [ ] Database queries are optimized
- [ ] No timeout errors

---

## Test Coverage Summary

| Component | Test Type | Location |
|-----------|-----------|----------|
| Signal handlers | Automated | NotificationSignalHandlerTests |
| Services (send/filter/cleanup) | Automated | NotificationServiceTests |
| Group filtering | Automated | NotificationGroupTests |
| Cleanup scheduling | Automated | NotificationCleanupTests |
| Integration flow | Automated | NotificationIntegrationTests |
| Dashboard UI | Manual | Section 2 |
| Notification center | Manual | Section 3 |
| Email delivery | Manual | Section 4 |
| WebSocket/Polling | Manual | Section 5 |
| Cleanup scheduling | Manual | Section 6 |
| Categories/Importance | Manual | Section 7 |
| Admin interface | Manual | Section 8 |
| Edge cases | Manual | Section 9 |
| Performance | Manual | Section 10 |

---

## Debugging Tips

### View notification bell JavaScript errors
1. Open browser DevTools → Console
2. Look for errors from `notifications.js`
3. Check WebSocket connection status

### Check scheduled jobs
```python
python manage.py shell
from django_apscheduler.models import DjangoJob
DjangoJob.objects.all()  # List all scheduled jobs
```

### View sent emails (development)
```python
python manage.py shell
from django.core.mail import outbox
for email in outbox:
    print(email.subject, email.to)
```

### Check notification database
```python
from notifications.models import Notification, NotificationRecipient
Notification.objects.all().values('title', 'category', 'importance', 'created_at')
NotificationRecipient.objects.filter(user_id=1).values('is_read', 'created_at', 'delivery_status')
```

---

## Validation Checklist

Before considering the notifications system "production-ready", verify:

- [ ] All automated tests pass (`python manage.py test notifications`)
- [ ] Manual tests completed for all 10 sections
- [ ] Email delivery works in target environment
- [ ] WebSocket connections work (or polling fallback verified)
- [ ] Cleanup scheduler runs automatically
- [ ] Dashboard integration is smooth (no JS errors)
- [ ] Performance is acceptable with large datasets
- [ ] Admin interface is usable and functions correctly
- [ ] Documentation is clear and complete
- [ ] Code follows Django/project conventions
- [ ] No security vulnerabilities (e.g., SQL injection, XSS)

---

## Post-Launch Monitoring

After deployment, monitor:

1. **Job Scheduler Health**
   - Check that cleanup jobs run daily
   - Monitor for job failures in DjangoJobExecution logs

2. **Email Delivery**
   - Monitor email bounce rates
   - Check spam folder for test emails
   - Verify email template rendering in production

3. **Database Growth**
   - Monitor NotificationRecipient table size
   - Ensure cleanup is removing old records
   - Watch for index performance

4. **User Engagement**
   - Track notification read rates
   - Monitor dashboard access patterns
   - Gather user feedback on notification usefulness

5. **System Health**
   - Monitor WebSocket connection stability
   - Check polling fallback usage rates
   - Watch for unusual error patterns
