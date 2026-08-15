# UPVC Pro - Backup & Restore System

Complete backup and restore functionality with scheduled automatic backups for SQLite database.

## Features

### Manual Backups
- ✅ Create backups on-demand with custom names
- ✅ Automatic timestamped backup filenames
- ✅ Backup to organized folder structure
- ✅ Export backups to external locations

### Restore Functionality
- ✅ Restore from any backup file
- ✅ Automatic pre-restore backup (safety measure)
- ✅ No data loss on restore operation
- ✅ Fast restoration using SQLite native API

### Scheduled Auto-Backup
- ✅ Configurable interval (default: every 6 hours)
- ✅ Enable/disable auto-backup
- ✅ Automatic old backup cleanup (keeps max 10)
- ✅ Force immediate backup option

### Backup Management
- ✅ List all backups with details
- ✅ View backup timestamps and sizes
- ✅ Delete old backups
- ✅ Database information API

---

## Backup Storage Location

**Default Backup Directory**:
```
%LOCALAPPDATA%\UPVC Pro\backups\
```

**Examples**:
- Windows: `C:\Users\YourName\AppData\Local\UPVC Pro\backups\`
- Database: `C:\Users\YourName\AppData\Local\UPVC Pro\upvc_pro.db`

**Backup Files**:
- Format: `upvc_backup_YYYYMMDD_HHMMSS.db`
- Example: `upvc_backup_20260816_143522.db`

---

## API Endpoints

### Database Information

#### Get Database Info
```http
GET /api/backup/database-info
```

**Response**:
```json
{
  "exists": true,
  "path": "C:\\Users\\...\\UPVC Pro\\upvc_pro.db",
  "size": 12345678,
  "size_mb": 12.34,
  "modified": "2026-08-16T14:35:22.123456",
  "modified_formatted": "2026-08-16 14:35:22",
  "tables": 18
}
```

**Access**: All authenticated users (no permission required)

---

### Manual Backups

#### Create Backup
```http
POST /api/backup/create
```

**Query Parameters**:
- `backup_name` (optional): Custom name for backup (without .db extension)

**Response**:
```json
{
  "success": true,
  "path": "C:\\Users\\...\\UPVC Pro\\backups\\upvc_backup_20260816_143522.db",
  "size": 12345678,
  "timestamp": "2026-08-16T14:35:22.123456",
  "filename": "upvc_backup_20260816_143522.db"
}
```

**Access**: Admin+ (requires user:read permission)

**Example**:
```bash
curl -X POST http://localhost:8000/api/backup/create?backup_name=before_upgrade \
  -H "Authorization: Bearer <token>"
```

#### List Backups
```http
GET /api/backup/list
```

**Response**:
```json
{
  "success": true,
  "backups": [
    {
      "filename": "upvc_backup_20260816_143522.db",
      "path": "C:\\Users\\...\\UPVC Pro\\backups\\upvc_backup_20260816_143522.db",
      "size": 12345678,
      "size_mb": 12.34,
      "created": "2026-08-16T14:35:22.123456",
      "created_formatted": "2026-08-16 14:35:22"
    }
  ],
  "count": 5,
  "backup_dir": "C:\\Users\\...\\UPVC Pro\\backups"
}
```

**Access**: Admin+ (requires user:read permission)

#### Delete Backup
```http
DELETE /api/backup/delete/{backup_file}
```

**Path Parameters**:
- `backup_file`: Filename (e.g., `upvc_backup_20260816_143522.db`)

**Response**:
```json
{
  "success": true,
  "message": "Backup deleted: upvc_backup_20260816_143522.db"
}
```

**Access**: SuperAdmin only (requires user:delete permission)

#### Export Backup
```http
POST /api/backup/export/{backup_file}
```

**Path Parameters**:
- `backup_file`: Filename to export

**Query Parameters**:
- `export_path`: Destination path (full path to save location)

**Response**:
```json
{
  "success": true,
  "message": "Backup exported to: D:\\backups\\upvc_backup_20260816_143522.db",
  "exported_path": "D:\\backups\\upvc_backup_20260816_143522.db"
}
```

**Access**: Admin+ (requires user:read permission)

**Example**:
```bash
curl -X POST "http://localhost:8000/api/backup/export/upvc_backup_20260816_143522.db?export_path=D:\\network_backup\\upvc_backup_20260816_143522.db" \
  -H "Authorization: Bearer <token>"
```

---

### Restore Operations

#### Restore from Backup
```http
POST /api/backup/restore/{backup_file}
```

**Path Parameters**:
- `backup_file`: Filename to restore from

**Response**:
```json
{
  "success": true,
  "message": "Database restored successfully",
  "restored_from": "upvc_backup_20260816_143522.db",
  "pre_restore_backup": "pre_restore_backup_20260816_143530.db"
}
```

**Access**: SuperAdmin only (requires user:delete permission)

**Important**:
- Automatic backup created before restore (saved as `pre_restore_backup_*.db`)
- Database locked during restore
- Application will need to be restarted after restore

**Example**:
```bash
curl -X POST "http://localhost:8000/api/backup/restore/upvc_backup_20260816_143522.db" \
  -H "Authorization: Bearer <token>"
```

---

### Scheduler Configuration

#### Get Scheduler Config
```http
GET /api/backup/scheduler/config
```

**Response**:
```json
{
  "enabled": true,
  "interval_hours": 6,
  "last_backup": "2026-08-16T14:35:22.123456",
  "next_backup": "2026-08-16T20:35:22.123456"
}
```

**Access**: Admin+ (requires user:read permission)

#### Update Scheduler Config
```http
PUT /api/backup/scheduler/config
```

**Query Parameters**:
- `enabled` (optional): true/false to enable/disable auto-backup
- `interval_hours` (optional): Hours between backups (minimum: 1)

**Response**:
```json
{
  "enabled": true,
  "interval_hours": 4,
  "last_backup": "2026-08-16T14:35:22.123456",
  "next_backup": "2026-08-16T18:35:22.123456"
}
```

**Access**: Admin+ (requires user:update permission)

**Example**:
```bash
# Change interval to every 4 hours
curl -X PUT "http://localhost:8000/api/backup/scheduler/config?interval_hours=4" \
  -H "Authorization: Bearer <token>"

# Disable auto-backup
curl -X PUT "http://localhost:8000/api/backup/scheduler/config?enabled=false" \
  -H "Authorization: Bearer <token>"
```

#### Force Immediate Backup
```http
POST /api/backup/scheduler/force
```

**Response**:
```json
{
  "success": true,
  "path": "C:\\Users\\...\\UPVC Pro\\backups\\manual_backup_20260816_143522.db",
  "size": 12345678,
  "timestamp": "2026-08-16T14:35:22.123456",
  "filename": "manual_backup_20260816_143522.db"
}
```

**Access**: Admin+ (requires user:create permission)

---

## Configuration File

**Location**: `%LOCALAPPDATA%\UPVC Pro\backup_config.json`

**Contents**:
```json
{
  "enabled": true,
  "interval_hours": 6,
  "last_backup": "2026-08-16T14:35:22.123456",
  "next_backup": "2026-08-16T20:35:22.123456"
}
```

**Manual Editing**:
- Can be edited directly with text editor
- Changes take effect immediately
- `interval_hours`: Minimum 1 hour, recommended 1-24 hours

---

## Default Settings

| Setting | Value | Notes |
|---------|-------|-------|
| Auto-Backup Enabled | Yes | Can be disabled via config |
| Backup Interval | 6 hours | Configurable: 1-24 hours |
| Max Backups Kept | 10 | Older backups auto-deleted |
| Backup Format | SQLite native | Consistent, corruption-proof |
| First Backup | On app start | If not done recently |

---

## Automatic Backup Schedule

**Default**: Every 6 hours

**Example Timeline** (App started at 08:00):
- 08:00 - App starts, check for backup
- 08:05 - First backup created (if needed)
- 14:05 - Second backup created
- 20:05 - Third backup created
- 02:05 - Fourth backup created
- And continues...

**Old Backups**: Kept in order of creation (newest first), deletion starts after 10th backup

---

## Backup Strategies

### For Production Systems

**Recommended Configuration**:
```json
{
  "enabled": true,
  "interval_hours": 4
}
```

**Backup Retention**:
- On-site: 10 daily backups (40 hours coverage)
- Off-site: Export weekly backups to network drive or USB

**Backup Testing**:
- Weekly: Restore test from oldest backup
- Verify data integrity
- Document restore time

### For Development

**Recommended Configuration**:
```json
{
  "enabled": true,
  "interval_hours": 12
}
```

**Manual Backups**:
- Before major operations
- Before data migrations
- Before version upgrades

---

## Disaster Recovery

### Complete System Recovery

1. **Install UPVC Pro** on new machine
2. **Stop the application**
3. **Place backup database** in `%LOCALAPPDATA%\UPVC Pro\`
4. **Rename** to `upvc_pro.db`
5. **Start application**
6. **Verify** data is correct

### Point-in-Time Recovery

1. **API Call**: Get list of backups
2. **Select** desired backup from timestamp
3. **API Call**: Restore from that backup
4. **Verify**: Check restored data
5. **Rollback** via pre-restore backup if needed

### Network Drive Backup

**Export Weekly**:
```bash
# Export to network drive
curl -X POST "http://localhost:8000/api/backup/export/upvc_backup_*.db?export_path=\\\\server\\backups\\upvc_backup_YYYYMMDD.db" \
  -H "Authorization: Bearer <token>"
```

**Restore from Network**:
```bash
# Restore from network backup
curl -X POST "http://localhost:8000/api/backup/restore/\\\\server\\backups\\upvc_backup_YYYYMMDD.db" \
  -H "Authorization: Bearer <token>"
```

---

## Monitoring Backups

### Check Last Backup
```bash
curl http://localhost:8000/api/backup/database-info \
  -H "Authorization: Bearer <token>"
```

### Verify Backup Files
```bash
# List all backups with timestamps
curl http://localhost:8000/api/backup/list \
  -H "Authorization: Bearer <token>"
```

### Monitor Backup Directory
- Location: `%LOCALAPPDATA%\UPVC Pro\backups\`
- Check size regularly: Should be ~10-15 MB per backup
- Disk space needed: ~200 MB for 10 backups

---

## Troubleshooting

### Backup Creation Fails

**Problem**: Backup creation returns error

**Solutions**:
1. Check disk space in `%LOCALAPPDATA%\UPVC Pro\`
2. Verify write permissions on backups folder
3. Ensure database is not locked (close app if needed)
4. Check disk is not full

### Restore Fails

**Problem**: Restore operation returns error

**Solutions**:
1. Verify backup file exists and is valid `.db` file
2. Ensure disk space for restore operation
3. Stop application before restore
4. Check user has SuperAdmin role
5. Verify backup file is not corrupted

### Auto-Backup Not Running

**Problem**: Scheduled backups not created

**Solutions**:
1. Check `backup_config.json` has `"enabled": true`
2. Verify application is running
3. Check interval setting (minimum 1 hour)
4. Monitor `last_backup` timestamp in config
5. Force backup via API to test

### Disk Space Issues

**Problem**: Not enough space for backups

**Solutions**:
1. Export older backups to external drive
2. Delete backups via API (keep 5 recent)
3. Reduce `interval_hours` (backup less frequently)
4. Disable auto-backup temporarily

---

## Migration to New System

### Step-by-Step Migration

1. **Create final backup** on old system:
   ```bash
   curl -X POST http://localhost:8000/api/backup/create?backup_name=final_backup \
     -H "Authorization: Bearer <token>"
   ```

2. **Export backup** to USB/Network:
   ```bash
   curl -X POST "http://localhost:8000/api/backup/export/upvc_backup_*.db?export_path=D:\\migration\\upvc_backup.db" \
     -H "Authorization: Bearer <token>"
   ```

3. **Install on new system** and configure

4. **Restore backup** on new system:
   ```bash
   curl -X POST "http://localhost:8000/api/backup/restore/upvc_backup.db" \
     -H "Authorization: Bearer <token>"
   ```

5. **Verify data** is correct and complete

---

## Future Viewer EXE

### ReadOnly Database Viewer

**Planned Feature**: Separate viewer EXE for read-only access

**Design**:
- Loads database from shared backup folder
- Always uses latest backup file
- Read-only mode (no modifications)
- No login required (or limited viewer access)
- Fast, lightweight UI

**Benefits**:
- View reports without modifying data
- Offline viewing of backup data
- Safe sharing of data with stakeholders
- No application license needed for viewers

**Implementation**:
1. Viewer EXE in read-only mode
2. Configurable backup folder path
3. Auto-refresh from latest backup
4. Lightweight viewer interface

---

## Summary

✅ **Backup Features**:
- Manual and scheduled backups
- Configurable auto-backup interval
- Automatic old backup cleanup
- Export to external locations
- Restore with safety measures

✅ **Restore Features**:
- Fast SQLite-native restore
- Pre-restore backup safety
- Point-in-time recovery
- Disaster recovery capability

✅ **Management**:
- API-based backup management
- Web UI for backups (ready for frontend)
- Configuration file for settings
- Monitoring and troubleshooting

---

## Version

**v1.0.0** (2026-08-16)

Complete backup and restore system with scheduled auto-backup, unlimited restore points, and disaster recovery support.
