# SharePoint Scheduler Auto-Purge Integration

## 🎯 Overview

The SharePoint scheduler now includes **automatic purge functionality** that runs after each successful indexing operation to clean up orphaned files from the search index.

## ✨ New Features

### 1. **Auto-Purge Configuration**
- **Scheduler Setting**: New `auto_purge_enabled` checkbox in the UI
- **Default**: Enabled by default for all new operations
- **Scope**: Applies to both scheduled and manual "Run Now" operations

### 2. **Automatic Workflow**
```
Indexing Operation → Success Check → Auto-Purge (if enabled) → Unified Report
```

### 3. **Enhanced Reporting**
- **Purge Results**: Included in all indexing reports
- **Summary Display**: Shows purge status in report list
- **Detailed View**: Full purge metrics in report details
- **Error Handling**: Purge errors are logged separately

## 🔧 Technical Implementation

### Modified Files
1. **`sharepoint_scheduler.py`**
   - Added `auto_purge_enabled` to `ScheduleConfig`
   - Enhanced `_run_indexing_operation()` with auto-purge logic
   - New `_run_auto_purge()` method
   - Updated report structure to include purge results

2. **`agentic-rag-demo.py`**
   - Added auto-purge checkbox in scheduler UI
   - Updated config objects to include auto-purge setting
   - Enhanced report display with purge information

### New Functionality

#### Auto-Purge Method
```python
def _run_auto_purge(self, index_name: str, selected_folders: List[str]) -> Dict[str, Any]:
    """Run automatic purge operation after indexing"""
    # Extracts target folder from selected folders
    # Creates SharepointDeletedFilesPurger instance
    # Runs purge operation asynchronously
    # Returns comprehensive results
```

#### Enhanced Reports
```json
{
    "id": "report_20250623_124530_scheduled",
    "type": "scheduled",
    "auto_purge_enabled": true,
    "purge_results": {
        "success": true,
        "message": "Successfully purged 5 orphaned document chunks",
        "documents_checked": 150,
        "files_checked": 25,
        "files_not_found": 2,
        "documents_deleted": 5
    }
}
```

## 📊 UI Enhancements

### Scheduler Configuration
- **Auto-Purge Checkbox**: `🗑️ Auto-purge after indexing`
- **Help Text**: "Automatically run purge to remove orphaned files after each indexing job"
- **Default**: Checked (enabled)

### Report Display
- **Summary**: Shows purge count in report list captions
- **Details**: Full purge metrics in expandable report view
- **Status**: Clear indication of auto-purge enabled/disabled

## 🚀 Benefits

### 1. **Fully Automated Maintenance**
- No manual intervention required
- Orphaned files are cleaned up immediately
- Index stays clean automatically

### 2. **Comprehensive Auditability**
- All purge operations are logged
- Unified reporting for indexing + purging
- Clear tracking of what was deleted

### 3. **Configurable Control**
- Can be enabled/disabled per operation
- Folder-specific purging based on indexed folders
- Consistent with existing purge logic

### 4. **Error Resilience**
- Purge failures don't stop indexing
- Errors are logged separately
- Graceful degradation if purge fails

## 🔄 Workflow Examples

### Scheduled Operation with Auto-Purge
1. **Trigger**: Scheduler runs at configured interval
2. **Index**: Process selected SharePoint folders
3. **Auto-Purge**: Clean up orphaned files (if enabled)
4. **Report**: Generate unified report with both results

### Manual "Run Now" with Auto-Purge
1. **Trigger**: User clicks "Run Now" button
2. **Index**: Process selected folders immediately  
3. **Auto-Purge**: Clean up orphaned files (if enabled)
4. **Report**: Show immediate results including purge data

## 📋 Configuration Options

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `auto_purge_enabled` | boolean | `true` | Enable automatic purge after indexing |
| `target_folder_path` | string | Extracted from folders | Folder-specific purging scope |
| `index_name` | string | From config | Target search index |

## 🎛️ Usage Instructions

### For Users
1. **Enable**: Check "Auto-purge after indexing" in scheduler settings
2. **Run**: Start scheduler or use "Run Now" - purging happens automatically
3. **Monitor**: Check reports for purge results and any errors

### For Developers
1. **Config**: Always include `auto_purge_enabled` in config objects
2. **Reports**: Check for `purge_results` in report objects
3. **Errors**: Handle purge errors separately from indexing errors

## 🎯 Result

The scheduler now provides **complete automated maintenance** for SharePoint indexing, ensuring that:
- ✅ Files are indexed efficiently
- ✅ Orphaned files are cleaned up automatically  
- ✅ Index stays optimized without manual intervention
- ✅ All operations are fully auditable

This eliminates the workflow gap where orphaned files detected in preview weren't automatically purged, creating a seamless end-to-end automation solution.
