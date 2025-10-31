# Email Notification Setup Guide

## Quick Setup

### 1. Create .env file

```bash
# Copy the example file
cp .env.example .env

# Edit it with your settings
nano .env
```

### 2. Configure Email Settings

Edit the `.env` file and update these settings:

```bash
# Enable email notifications
EMAIL_ENABLED=true

# SMTP Server Settings
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true

# Your email credentials
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password-here

# Email addresses
EMAIL_FROM=your-email@gmail.com
EMAIL_TO=recipient@example.com
```

## Gmail Setup (Recommended)

### Step 1: Enable 2-Factor Authentication
1. Go to https://myaccount.google.com/security
2. Click "2-Step Verification"
3. Follow the steps to enable it

### Step 2: Generate App Password
1. Go to https://myaccount.google.com/apppasswords
2. Select app: "Mail"
3. Select device: "Other (Custom name)"
4. Enter: "Dakimakura Scraper"
5. Click "Generate"
6. Copy the 16-character password (e.g., `abcd efgh ijkl mnop`)
7. **Use this password** (without spaces) in your `.env` file as `SMTP_PASSWORD`

### Example Gmail Configuration

```bash
EMAIL_ENABLED=true
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=yourname@gmail.com
SMTP_PASSWORD=abcdefghijklmnop
EMAIL_FROM=yourname@gmail.com
EMAIL_TO=yourname@gmail.com
```

## Other Email Providers

### Outlook/Hotmail
```bash
SMTP_SERVER=smtp-mail.outlook.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@outlook.com
SMTP_PASSWORD=your-password
```

### Yahoo Mail
```bash
SMTP_SERVER=smtp.mail.yahoo.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@yahoo.com
SMTP_PASSWORD=your-app-password
```

### QQ Mail (China)
```bash
SMTP_SERVER=smtp.qq.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-qq-number@qq.com
SMTP_PASSWORD=your-authorization-code
```

## Testing Email Configuration

Test your email setup before running the scraper:

```bash
python main.py test-email
```

If successful, you should see:
```
✅ 邮件配置测试成功
```

If it fails, check:
- ✓ Email and password are correct
- ✓ App password (not regular password) for Gmail
- ✓ 2-factor authentication is enabled (for Gmail)
- ✓ SMTP server and port are correct
- ✓ No firewall blocking port 587

## Using Email Notifications

### Option 1: Automatic notifications when running scraper

```bash
# Run scraper with email notifications (default)
python main.py run

# This will:
# 1. Scrape all platforms
# 2. Detect changes (new items, price changes, etc.)
# 3. Send email if changes found
```

### Option 2: Send daily report manually

```bash
# Send a daily report email with full table
python main.py daily-report
```

### Option 3: Run without email

```bash
# Scrape without sending emails
python main.py run --no-email
```

## Email Content

### Change Notification Email

When changes are detected, you'll receive an email like:

**Subject:** 🔔 发现 2 个新商品！

**Content:**
```
🎉 新发现的商品
• 【原神】抱き枕カバー 神里綾華 - ¥19,380
  查看商品 → https://jp.mercari.com/item/...

💰 价格变化
• 【崩坏】キャストリス 抱き枕カバー
  价格: ¥25,000 → ¥22,000

[Full comparison table attached]
```

### Daily Report Email

**Subject:** 抱枕套监控 - 每日报告 (2025-10-31)

**Content:**
- Summary statistics
- Full 4×7 comparison table
- Links to all available items

## Notification Preferences

You can control what triggers email notifications in `.env`:

```bash
# Control what events trigger notifications
NOTIFY_ON_NEW_ITEMS=true       # New items found
NOTIFY_ON_PRICE_CHANGE=true    # Price changes
NOTIFY_ON_SOLD_OUT=true        # Items sold out
NOTIFY_ON_CREATOR_UPDATES=true # Creator announcements
```

## Troubleshooting

### Error: "Authentication failed"
- Make sure you're using an **app password**, not your regular Gmail password
- Enable 2-factor authentication first

### Error: "Connection timeout"
- Check firewall/antivirus isn't blocking port 587
- Try port 465 with SSL instead (set `SMTP_PORT=465`)

### Error: "Email not enabled"
- Make sure `EMAIL_ENABLED=true` in your `.env` file
- The `.env` file must be in the project root directory

### No email received
- Check spam/junk folder
- Verify `EMAIL_TO` address is correct
- Run `python main.py test-email` to test connection

## Schedule Automatic Emails

You can set up a cron job (Linux/Mac) or Task Scheduler (Windows) to run automatically:

### Mac/Linux (cron)

```bash
# Edit crontab
crontab -e

# Add these lines to run twice daily at 9 AM and 9 PM
0 9 * * * cd /path/to/scraper && /path/to/python main.py run
0 21 * * * cd /path/to/scraper && /path/to/python main.py run
```

### Windows (Task Scheduler)

1. Open Task Scheduler
2. Create Basic Task
3. Trigger: Daily at 9:00 AM
4. Action: Start a program
   - Program: `C:\path\to\python.exe`
   - Arguments: `main.py run`
   - Start in: `C:\path\to\scraper`
5. Repeat for 9:00 PM

## Example Workflow

```bash
# 1. First time setup
cp .env.example .env
nano .env  # Configure email settings

# 2. Test email
python main.py test-email

# 3. Initialize database
python main.py init-db

# 4. First run (with browser visible to see what's happening)
python main.py run --show-browser

# 5. Check report
python main.py report --html -o report.html
open report.html  # or start report.html on Windows

# 6. Send test daily report
python main.py daily-report

# 7. Set up cron job for automatic runs
```

That's it! You're now set up to receive automatic email notifications whenever new dakimakura items are found or prices change.
