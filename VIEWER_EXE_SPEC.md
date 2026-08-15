# UPVC Pro Viewer EXE - Specification

## Overview

A lightweight, read-only desktop application for viewing UPVC Pro reports and data from backup database files. Designed for stakeholders who need data access without modification capabilities.

## Purpose

- **View-only access** to reports and customer data
- **No database locks** - works with backup files
- **No application license** - lightweight alternative
- **Automatic updates** - loads latest backup file
- **Offline capable** - works without server connection
- **Fast startup** - minimal dependencies

## Key Features

### Read-Only Mode
- ✅ All reports accessible (GSTR-1, P&L, Balance Sheet, etc.)
- ✅ View customer/vendor data
- ✅ View invoices, quotations, payments
- ✅ Search and filter functionality
- ✅ PDF download (view only)
- ✅ CSV export (view only)
- ❌ No create/update/delete operations
- ❌ No data modification
- ❌ No user management access

### Data Source
- **Primary**: Latest backup from configured folder
- **Refresh**: Auto-check for newer backups on startup
- **Connection**: Load-once at startup (no live connection)
- **Locking**: No database locks (backup file never modified)

### User Interface
- **Same as Main App**: All pages available
- **Disabled Operations**: Create, Edit, Delete buttons hidden
- **Read-Only Mode**: Enforced at API level
- **Navigation**: Full access to all report pages
- **Export**: Download reports as PDF/CSV

## Backup Folder Configuration

**Folder Location**: User-selected on first launch

**Folder Structure**:
```
C:\Users\Public\UPVC Backups\
├── upvc_backup_20260810_100000.db
├── upvc_backup_20260812_100000.db
├── upvc_backup_20260814_100000.db  ← Latest (loaded)
├── upvc_backup_20260816_100000.db  ← Newest
└── ...
```

**Auto-Load**: Latest `upvc_backup_*.db` file by timestamp

**Configuration File**: `%APPDATA%\UPVC Viewer\viewer_config.json`

## Implementation Steps

### Step 1: Backend Read-Only Mode (1 day)
```python
# Read-only database connection
sqlite3.connect(f'file:{db_path}?mode=ro', uri=True)

# Disable mutations at API level
/api/*  → Allow GET, Deny POST/PUT/DELETE
```

### Step 2: Viewer Launcher (1 day)
- Find latest backup in folder
- Connect as read-only
- Load database once at startup
- No live connection needed

### Step 3: Frontend Read-Only UI (1 day)
- Hide all edit/create/delete buttons
- Show "Read-Only" indicator
- Disable form inputs
- Block mutation API calls

### Step 4: PyInstaller Bundle (1 day)
- Create `UPVC Viewer.spec`
- Bundle with backend + frontend
- Size: ~100-120 MB
- Standalone executable

### Step 5: Testing & Installer (2 days)
- NSIS installer creation
- User-friendly setup wizard
- Backup folder selection prompt
- Desktop shortcut creation

## Usage Scenarios

### Scenario 1: Manager Daily Reviews
1. Open UPVC Viewer
2. Automatically loads latest backup
3. View reports (GSTR, P&L, Cash Flow)
4. Export to PDF/CSV
5. Share with team

### Scenario 2: Stakeholder Access
1. Manager exports backup to shared folder
2. Stakeholder runs UPVC Viewer
3. Points to shared backup folder
4. Reads reports (no passwords, no license)
5. Cannot modify any data

### Scenario 3: Offline Reporting
1. Backup file copied to laptop
2. Launch UPVC Viewer
3. Point to local backup file
4. Works completely offline
5. All reports accessible

### Scenario 4: Multiple Concurrent Users
1. Central backup folder on network
2. 5+ users run UPVC Viewer
3. All load same backup file
4. No locking conflicts
5. Independent sessions

## Security

### Data Protection
- ✅ SQLite read-only mode enforced
- ✅ No mutations possible
- ✅ Backup files never modified
- ✅ No credentials stored

### Access Control
- ✅ Read-only at API level
- ✅ All writes rejected
- ✅ No authentication required
- ✅ Standalone deployment

### Considerations
- User can copy backup file (expected)
- All report data visible (intentional for reports)
- Sensitive data? Use encrypted backups
- Network access? Add VPN + folder permissions

## Timeline

| Task | Days | Status |
|------|------|--------|
| Backend read-only | 1 | Planned |
| Launcher creation | 1 | Planned |
| Frontend UI updates | 1 | Planned |
| PyInstaller bundle | 1 | Planned |
| Testing & installer | 2 | Planned |
| **Total** | **6 days** | **After Phase 3** |

## Distribution

**Deliverables**:
- UPVC Viewer.exe (~100 MB)
- UPVC Viewer Installer.exe (~50 MB)
- README with setup instructions
- Backup folder setup guide

**Installation**:
1. Run installer
2. Choose installation folder
3. Create desktop shortcut
4. Launch app (first run asks for backup folder)
5. Ready to view reports

## Summary

**UPVC Pro Viewer** enables:
- Stakeholder access without licenses
- Offline report viewing
- Safe data sharing (backup files are immutable)
- No database locking issues
- Lightweight alternative to main EXE

**Next Steps**: Implement after main UPVC Pro EXE is built and tested

**Estimated**: 6 days development + QA
