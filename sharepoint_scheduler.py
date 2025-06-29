"""
SharePoint Indexing Scheduler
Handles scheduled indexing operations with parallel processing and reporting
"""

import threading
import time
import json
import os
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
from dataclasses import dataclass, asdict
import uuid
import pickle  # For state persistence
import warnings


# Suppress Streamlit warnings when running in background threads
class StreamlitWarningFilter(logging.Filter):
    def filter(self, record):
        if "missing ScriptRunContext" in record.getMessage():
            return False
        return True

# Apply the filter to suppress Streamlit warnings
logging.getLogger().addFilter(StreamlitWarningFilter())


# Global instance to ensure singleton behavior
_scheduler_instance = None
_scheduler_lock = threading.Lock()


@dataclass
class FileTrackingInfo:
    """Information about a tracked file"""
    file_id: str
    file_name: str
    file_path: str
    folder_key: str
    last_modified: str
    file_size: int
    etag: Optional[str] = None
    content_hash: Optional[str] = None
    last_indexed: Optional[str] = None
    index_name: Optional[str] = None


@dataclass
class ScheduleConfig:
    """Configuration for scheduled indexing"""
    id: str
    name: str
    selected_folders: List[str]
    index_name: str
    file_types: Optional[List[str]]
    interval_minutes: int
    enabled: bool
    max_parallel_files: int = 3
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    created_at: str = None
    change_detection_enabled: bool = True  # New: enable change detection
    force_full_reindex: bool = False  # New: force full reindex on next run
    auto_purge_enabled: bool = True  # New: automatically run purge after indexing
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()


class SharePointScheduler:
    """Manages scheduled SharePoint indexing operations with enhanced features"""
    
    def __init__(self, config_file: str = "sharepoint_schedules.json"):
        self.config_file = config_file
        self.state_file = "scheduler_state.pkl"  # For persisting runtime state
        self.schedules: Dict[str, ScheduleConfig] = {}
        self.running_jobs: Dict[str, threading.Thread] = {}
        self.stop_flags: Dict[str, threading.Event] = {}
        self.reports_dir = "sharepoint_reports"
        self.current_status = "Stopped"
        self.interval_minutes = 15  # Default to 15 minutes instead of 1 minute
        self.is_running = False
        self.scheduler_thread = None
        self.last_run = None
        self.next_run = None
        self.selected_folders = []
        self.config = {}
        self.max_parallel_files = 3
        self.lock = threading.Lock()
        
        # Ensure reports directory exists
        os.makedirs(self.reports_dir, exist_ok=True)
        
        # Load persisted state
        self._load_state()
    
    @staticmethod
    def get_instance(config_file: str = "sharepoint_schedules.json"):
        """Get singleton instance of the scheduler"""
        global _scheduler_instance
        with _scheduler_lock:
            if _scheduler_instance is None:
                _scheduler_instance = SharePointScheduler(config_file)
            return _scheduler_instance
    
    def _save_state(self):
        """Save current scheduler state to file"""
        try:
            state = {
                'is_running': self.is_running,
                'current_status': self.current_status,
                'interval_minutes': self.interval_minutes,
                'last_run': self.last_run.isoformat() if self.last_run else None,
                'next_run': self.next_run.isoformat() if self.next_run else None,
                'selected_folders': self.selected_folders,
                'config': self.config,
                'max_parallel_files': self.max_parallel_files
            }
            with open(self.state_file, 'wb') as f:
                pickle.dump(state, f)
        except Exception as e:
            logging.error(f"Failed to save scheduler state: {e}")
    
    def _load_state(self):
        """Load scheduler state from file"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'rb') as f:
                    state = pickle.load(f)
                
                self.current_status = state.get('current_status', 'Stopped')
                self.interval_minutes = state.get('interval_minutes', 5)
                self.selected_folders = state.get('selected_folders', [])
                self.config = state.get('config', {})
                self.max_parallel_files = state.get('max_parallel_files', 3)
                
                # Handle datetime fields
                if state.get('last_run'):
                    self.last_run = datetime.fromisoformat(state['last_run'])
                if state.get('next_run'):
                    self.next_run = datetime.fromisoformat(state['next_run'])
                
                # Check if scheduler should still be running
                was_running = state.get('is_running', False)
                if was_running:
                    # Don't auto-resume scheduler - wait for explicit user action
                    logging.info("Scheduler was running before restart, but auto-resume is disabled for user control.")
                    self.is_running = False
                    self.current_status = "Stopped (needs manual restart)"
                    
        except Exception as e:
            logging.error(f"Failed to load scheduler state: {e}")
    
    def _resume_scheduler(self):
        """Resume scheduler after restart"""
        try:
            if not self.is_running and self.selected_folders and self.config:
                self.is_running = True
                self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
                self.scheduler_thread.start()
                logging.info("Scheduler resumed successfully")
        except Exception as e:
            logging.error(f"Failed to resume scheduler: {e}")
            self.is_running = False
            self.current_status = "Error"
    
    def set_interval(self, minutes: int):
        """Set the scheduler interval in minutes (1-1440 for 24 hours)"""
        self.interval_minutes = max(1, min(1440, minutes))
        if self.is_running:
            self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
        self._save_state()
    
    def start_scheduler(self, selected_folders: List[str], config: Dict[str, Any]):
        """Start the scheduler with given configuration"""
        if self.is_running:
            return {"success": False, "message": "Scheduler is already running"}
        
        # Validate that folders are explicitly selected by user
        if not selected_folders or len(selected_folders) == 0:
            return {"success": False, "message": "No folders selected. Please select folders to monitor before starting the scheduler."}
        
        try:
            self.is_running = True
            self.current_status = "Starting..."
            self.next_run = datetime.now() + timedelta(minutes=self.interval_minutes)
            
            # Store configuration
            self.selected_folders = selected_folders
            self.config = config
            self.max_parallel_files = config.get('max_parallel_files', 3)
            
            # Start scheduler thread
            self.scheduler_thread = threading.Thread(target=self._scheduler_loop, daemon=True)
            self.scheduler_thread.start()
            
            self.current_status = "Running"
            self._save_state()
            logging.info(f"SharePoint scheduler started with {self.interval_minutes} minute interval")
            
            return {
                "success": True, 
                "message": f"Scheduler started successfully. Next run: {self.next_run.strftime('%H:%M:%S')}"
            }
            
        except Exception as e:
            self.is_running = False
            self.current_status = "Error"
            self._save_state()
            logging.error(f"Failed to start scheduler: {e}")
            return {"success": False, "message": f"Failed to start scheduler: {str(e)}"}
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        if not self.is_running:
            return {"success": False, "message": "Scheduler is not running"}
        
        try:
            self.is_running = False
            self.current_status = "Stopping..."
            
            # Wait for current thread to finish
            if self.scheduler_thread and self.scheduler_thread.is_alive():
                self.scheduler_thread.join(timeout=10)
            
            self.current_status = "Stopped"
            self.next_run = None
            self._save_state()
            logging.info("SharePoint scheduler stopped")
            
            return {"success": True, "message": "Scheduler stopped successfully"}
            
        except Exception as e:
            self.current_status = "Error"
            self._save_state()
            logging.error(f"Failed to stop scheduler: {e}")
            return {"success": False, "message": f"Failed to stop scheduler: {str(e)}"}
    
    def run_now(self, selected_folders: List[str], config: Dict[str, Any]):
        """Run indexing immediately with parallel processing"""
        try:
            self.current_status = "Running Manual Index..."
            
            # Run indexing operation
            result = self._run_indexing_operation(selected_folders, config, is_manual=True)
            
            if not self.is_running:  # Only update status if not scheduled running
                self.current_status = "Stopped"
            
            return result
            
        except Exception as e:
            logging.error(f"Manual indexing failed: {e}")
            if not self.is_running:
                self.current_status = "Stopped"
            return {"success": False, "message": f"Manual indexing failed: {str(e)}"}
    
    def _scheduler_loop(self):
        """Main scheduler loop"""
        logging.info("Scheduler loop started")
        while self.is_running:
            try:
                now = datetime.now()
                
                # Debug logging
                if self.next_run:
                    time_until = (self.next_run - now).total_seconds()
                    logging.debug(f"Scheduler: Current time: {now.strftime('%H:%M:%S')}, Next run: {self.next_run.strftime('%H:%M:%S')}, Time until: {time_until:.0f}s")
                else:
                    logging.debug(f"Scheduler: No next run scheduled")
                
                if self.next_run and now >= self.next_run:
                    logging.info(f"Scheduler: Starting scheduled indexing operation at {now.strftime('%H:%M:%S')}")
                    self.current_status = "Running Scheduled Index..."
                    self._save_state()
                    
                    # Run indexing operation
                    result = self._run_indexing_operation(
                        self.selected_folders, 
                        self.config, 
                        is_manual=False
                    )
                    
                    # Schedule next run
                    self.last_run = now
                    self.next_run = now + timedelta(minutes=self.interval_minutes)
                    logging.info(f"Scheduler: Completed indexing operation. Next run scheduled for {self.next_run.strftime('%H:%M:%S')}")
                    
                    if self.is_running:  # Only update if still running
                        self.current_status = "Running"
                        self._save_state()  # Save state after each run
                
                # Sleep for 15 seconds before checking again (more responsive)
                time.sleep(15)
                
            except Exception as e:
                logging.error(f"Scheduler loop error: {e}")
                if self.is_running:
                    self.current_status = "Error"
                    self._save_state()
                time.sleep(60)  # Wait before retrying
        
        logging.info("Scheduler loop ended")
    
    def _run_indexing_operation(self, selected_folders: List[str], config: Dict[str, Any], is_manual: bool = False):
        """Run the actual indexing operation with parallel processing and optional purging"""
        start_time = datetime.now()
        report_id = f"report_{start_time.strftime('%Y%m%d_%H%M%S')}_{'manual' if is_manual else 'scheduled'}"
        
        report = {
            "id": report_id,
            "start_time": start_time.isoformat(),
            "end_time": None,
            "type": "manual" if is_manual else "scheduled",
            "folders": selected_folders,
            "files_processed": 0,
            "files_successful": 0,
            "files_failed": 0,
            "chunks_created": 0,
            "errors": [],
            "processing_details": [],
            "status": "running",
            "auto_purge_enabled": config.get('auto_purge_enabled', True),
            "purge_results": None
        }
        
        try:
            # Get SharePoint manager
            from sharepoint_index_manager import SharePointIndexManager
            manager = SharePointIndexManager()
            
            # Get files from selected folders
            all_files = []
            for folder_key in selected_folders:
                try:
                    # Parse folder key: site_domain|site_name|drive_name|folder_path
                    parts = folder_key.split('|', 3)
                    if len(parts) == 4:
                        site_domain, site_name, drive_name, folder_path = parts
                        files = manager.get_files_from_folder(
                            site_domain, site_name, drive_name, folder_path
                        )
                        all_files.extend(files)
                except Exception as e:
                    error_msg = f"Error getting files from folder {folder_key}: {str(e)}"
                    report["errors"].append(error_msg)
                    logging.error(error_msg)
            
            report["files_processed"] = len(all_files)
            
            if not all_files:
                report["status"] = "completed"
                report["end_time"] = datetime.now().isoformat()
                self._save_report(report)
                return {"success": True, "message": "No files found to index", "report_id": report_id}
            
            # Process files in parallel
            max_workers = config.get('max_parallel_files', self.max_parallel_files)
            successful_files = []
            failed_files = []
            total_chunks = 0
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # Submit all file processing tasks
                future_to_file = {
                    executor.submit(self._process_single_file, file_info, config, manager): file_info 
                    for file_info in all_files
                }
                
                # Process completed tasks
                for future in as_completed(future_to_file):
                    file_info = future_to_file[future]
                    try:
                        result = future.result()
                        if result["success"]:
                            successful_files.append(file_info)
                            total_chunks += result.get("chunks", 0)
                            report["processing_details"].append({
                                "file": file_info.get("name", "Unknown"),
                                "status": "success",
                                "chunks": result.get("chunks", 0),
                                "method": result.get("method", "unknown")
                            })
                        else:
                            failed_files.append(file_info)
                            error_msg = f"Failed to process {file_info.get('name', 'Unknown')}: {result.get('error', 'Unknown error')}"
                            report["errors"].append(error_msg)
                            report["processing_details"].append({
                                "file": file_info.get("name", "Unknown"),
                                "status": "failed",
                                "error": result.get("error", "Unknown error")
                            })
                    except Exception as e:
                        failed_files.append(file_info)
                        error_msg = f"Exception processing {file_info.get('name', 'Unknown')}: {str(e)}"
                        report["errors"].append(error_msg)
                        report["processing_details"].append({
                            "file": file_info.get("name", "Unknown"),
                            "status": "failed",
                            "error": str(e)
                        })
            
            # Update report
            report["files_successful"] = len(successful_files)
            report["files_failed"] = len(failed_files)
            report["chunks_created"] = total_chunks
            report["status"] = "completed"
            report["end_time"] = datetime.now().isoformat()
            
            # Run auto-purge if enabled and indexing was successful
            if config.get('auto_purge_enabled', True) and len(successful_files) > 0:
                logging.info("Running automatic purge after successful indexing...")
                purge_result = self._run_auto_purge(config.get('index_name'), selected_folders)
                report["purge_results"] = purge_result
                
                if purge_result.get("success"):
                    logging.info(f"Auto-purge completed: {purge_result.get('message', 'No message')}")
                else:
                    error_msg = f"Auto-purge failed: {purge_result.get('message', 'Unknown error')}"
                    report["errors"].append(error_msg)
                    logging.error(error_msg)
            
            # Save report
            self._save_report(report)
            
            success_msg = f"Indexing completed: {len(successful_files)} files successful, {len(failed_files)} failed, {total_chunks} chunks created"
            if report.get("purge_results"):
                purge_msg = report["purge_results"].get("message", "")
                success_msg += f". Auto-purge: {purge_msg}"
            logging.info(success_msg)
            
            return {
                "success": True,
                "message": success_msg,
                "report_id": report_id,
                "files_successful": len(successful_files),
                "files_failed": len(failed_files),
                "chunks_created": total_chunks
            }
            
        except Exception as e:
            report["status"] = "error"
            report["end_time"] = datetime.now().isoformat()
            report["errors"].append(f"Indexing operation failed: {str(e)}")
            self._save_report(report)
            
            error_msg = f"Indexing operation failed: {str(e)}"
            logging.error(error_msg)
            return {"success": False, "message": error_msg, "report_id": report_id}
    
    def _run_auto_purge(self, index_name: str, selected_folders: List[str]) -> Dict[str, Any]:
        """Run automatic purge operation after indexing"""
        try:
            import asyncio
            from connectors.sharepoint.sharepoint_deleted_files_purger import SharepointDeletedFilesPurger
            
            # Determine target folder for purging
            target_folder_path = None
            if selected_folders:
                # Extract folder path from the first selected folder
                # Format: site_domain|site_name|drive_name|folder_path
                folder_key = selected_folders[0]
                if '|' in folder_key:
                    parts = folder_key.split('|', 3)
                    if len(parts) == 4:
                        target_folder_path = parts[3]  # Extract folder_path
            
            # Create purger instance
            purger = SharepointDeletedFilesPurger(
                index_name=index_name,
                target_folder_path=target_folder_path
            )
            
            # Run purge operation asynchronously
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(purger.purge_deleted_files())
                return result
            finally:
                loop.close()
                
        except Exception as e:
            error_msg = f"Auto-purge failed: {str(e)}"
            logging.error(error_msg)
            return {
                "success": False,
                "message": error_msg,
                "documents_checked": 0,
                "documents_deleted": 0,
                "files_checked": 0,
                "files_not_found": 0,
                "errors": [str(e)]
            }

    def _process_single_file(self, file_info: Dict[str, Any], config: Dict[str, Any], manager) -> Dict[str, Any]:
        """Process a single file and return results"""
        try:
            # Get index name from config
            index_name = config.get('index_name')
            
            # Use the sharepoint manager's index_files method
            result = manager.index_files([file_info], index_name=index_name)
            
            if result.get("success", False):
                processing_results = result.get("processing_results", [])
                if processing_results:
                    first_result = processing_results[0]
                    return {
                        "success": True,
                        "chunks": first_result.get("chunks", 0),
                        "method": first_result.get("extraction_method", "unknown")
                    }
                else:
                    return {
                        "success": True,
                        "chunks": result.get("total_chunks", 0),
                        "method": "unknown"
                    }
            else:
                return {
                    "success": False,
                    "error": result.get("message", "Unknown error")
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }
    
    def _save_report(self, report: Dict[str, Any]):
        """Save report to file"""
        try:
            report_file = os.path.join(self.reports_dir, f"{report['id']}.json")
            with open(report_file, 'w') as f:
                json.dump(report, f, indent=2)
        except Exception as e:
            logging.error(f"Failed to save report: {e}")
    
    def get_reports(self) -> List[Dict[str, Any]]:
        """Get list of all reports"""
        reports = []
        try:
            if os.path.exists(self.reports_dir):
                for filename in os.listdir(self.reports_dir):
                    if filename.endswith('.json'):
                        try:
                            report_file = os.path.join(self.reports_dir, filename)
                            with open(report_file, 'r') as f:
                                report = json.load(f)
                                reports.append(report)
                        except Exception as e:
                            logging.error(f"Failed to load report {filename}: {e}")
            
            # Sort by start time (newest first)
            reports.sort(key=lambda x: x.get('start_time', ''), reverse=True)
        except Exception as e:
            logging.error(f"Failed to get reports: {e}")
        
        return reports
    
    def delete_report(self, report_id: str) -> Dict[str, Any]:
        """Delete a report from history"""
        try:
            report_file = os.path.join(self.reports_dir, f"{report_id}.json")
            if os.path.exists(report_file):
                os.remove(report_file)
                return {"success": True, "message": f"Report {report_id} deleted successfully"}
            else:
                return {"success": False, "message": f"Report {report_id} not found"}
        except Exception as e:
            logging.error(f"Failed to delete report {report_id}: {e}")
            return {"success": False, "message": f"Failed to delete report: {str(e)}"}
    
    def delete_all_reports(self) -> Dict[str, Any]:
        """Delete all reports from history"""
        try:
            if not os.path.exists(self.reports_dir):
                return {"success": True, "message": "No reports to delete", "deleted_count": 0}
            
            deleted_count = 0
            errors = []
            
            # Get all report files
            for filename in os.listdir(self.reports_dir):
                if filename.endswith('.json'):
                    try:
                        report_file = os.path.join(self.reports_dir, filename)
                        os.remove(report_file)
                        deleted_count += 1
                    except Exception as e:
                        error_msg = f"Failed to delete {filename}: {str(e)}"
                        errors.append(error_msg)
                        logging.error(error_msg)
            
            if errors:
                return {
                    "success": False, 
                    "message": f"Deleted {deleted_count} reports but encountered {len(errors)} errors",
                    "deleted_count": deleted_count,
                    "errors": errors
                }
            else:
                return {
                    "success": True, 
                    "message": f"Successfully deleted all {deleted_count} reports",
                    "deleted_count": deleted_count
                }
                
        except Exception as e:
            logging.error(f"Failed to delete all reports: {e}")
            return {"success": False, "message": f"Failed to delete all reports: {str(e)}", "deleted_count": 0}
    
    def get_status(self) -> Dict[str, Any]:
        """Get current scheduler status with recent job history"""
        # Get recent reports for status
        recent_reports = self.get_recent_reports(5)
        last_job_status = "No jobs yet"
        
        if recent_reports and recent_reports.get('reports'):
            latest_report = recent_reports['reports'][0]
            if latest_report.get('status') == 'completed':
                last_job_status = "✅ Success"
            elif latest_report.get('status') == 'failed':
                last_job_status = "❌ Failed"
            else:
                last_job_status = "🔄 Running"
        
        return {
            "is_running": self.is_running,
            "status": self.current_status,
            "interval_minutes": self.interval_minutes,
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "selected_folders_count": len(getattr(self, 'selected_folders', [])),
            "max_parallel_files": self.max_parallel_files,
            "last_job_status": last_job_status,
            "recent_reports": recent_reports.get('reports', [])[:3] if recent_reports else []
        }
    
    def get_recent_reports(self, limit: int = 5) -> Dict[str, Any]:
        """Get recent reports with limit"""
        try:
            reports = self.get_reports()
            limited_reports = reports[:limit] if reports else []
            
            return {
                "reports": limited_reports,
                "total_count": len(reports) if reports else 0
            }
        except Exception as e:
            logging.error(f"Failed to get recent reports: {e}")
            return {
                "reports": [],
                "total_count": 0
            }
    
    def load_schedules(self):
        """Load schedules from file"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    data = json.load(f)
                    for schedule_id, schedule_data in data.items():
                        self.schedules[schedule_id] = ScheduleConfig(**schedule_data)
        except Exception as e:
            logging.error(f"Error loading schedules: {e}")
    
    def save_schedules(self):
        """Save schedules to file"""
        try:
            data = {}
            for schedule_id, schedule in self.schedules.items():
                data[schedule_id] = asdict(schedule)
            
            with open(self.config_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving schedules: {e}")
    
    def create_schedule(self, name: str, selected_folders: List[str], index_name: str, 
                       file_types: Optional[List[str]], interval_minutes: int, 
                       auto_purge_enabled: bool = True) -> str:
        """Create a new schedule"""
        schedule_id = str(uuid.uuid4())
        schedule = ScheduleConfig(
            id=schedule_id,
            name=name,
            selected_folders=selected_folders,
            index_name=index_name,
            file_types=file_types,
            interval_minutes=interval_minutes,
            enabled=False,
            auto_purge_enabled=auto_purge_enabled
        )
        
        self.schedules[schedule_id] = schedule
        self.save_schedules()
        return schedule_id
    
    def update_schedule(self, schedule_id: str, **kwargs):
        """Update an existing schedule"""
        if schedule_id in self.schedules:
            schedule = self.schedules[schedule_id]
            for key, value in kwargs.items():
                if hasattr(schedule, key):
                    setattr(schedule, key, value)
            self.save_schedules()
    
    def delete_schedule(self, schedule_id: str):
        """Delete a schedule"""
        if schedule_id in self.schedules:
            self.stop_schedule(schedule_id)
            del self.schedules[schedule_id]
            self.save_schedules()
    
    def start_schedule(self, schedule_id: str):
        """Start a scheduled job"""
        if schedule_id not in self.schedules:
            return False
        
        if schedule_id in self.running_jobs and self.running_jobs[schedule_id].is_alive():
            return False  # Already running
        
        schedule = self.schedules[schedule_id]
        schedule.enabled = True
        
        # Calculate next run time
        next_run = datetime.now() + timedelta(minutes=schedule.interval_minutes)
        schedule.next_run = next_run.isoformat()
        
        # Create stop flag
        stop_flag = threading.Event()
        self.stop_flags[schedule_id] = stop_flag
        
        # Start background thread
        job_thread = threading.Thread(
            target=self._run_scheduled_job,
            args=(schedule_id, stop_flag),
            daemon=True
        )
        self.running_jobs[schedule_id] = job_thread
        job_thread.start()
        
        self.save_schedules()
        return True
    
    def stop_schedule(self, schedule_id: str):
        """Stop a scheduled job"""
        if schedule_id in self.schedules:
            self.schedules[schedule_id].enabled = False
            self.schedules[schedule_id].next_run = None
        
        if schedule_id in self.stop_flags:
            self.stop_flags[schedule_id].set()
        
        if schedule_id in self.running_jobs:
            # Wait for thread to finish (with timeout)
            self.running_jobs[schedule_id].join(timeout=5.0)
            del self.running_jobs[schedule_id]
        
        if schedule_id in self.stop_flags:
            del self.stop_flags[schedule_id]
        
        self.save_schedules()
    
    def run_schedule_now(self, schedule_id: str):
        """Run a schedule immediately"""
        if schedule_id not in self.schedules:
            return False
        
        schedule = self.schedules[schedule_id]
        
        # Run in background thread
        run_thread = threading.Thread(
            target=self._execute_indexing,
            args=(schedule,),
            daemon=True
        )
        run_thread.start()
        return True
    
    def _run_scheduled_job(self, schedule_id: str, stop_flag: threading.Event):
        """Background job runner"""
        schedule = self.schedules[schedule_id]
        
        while not stop_flag.is_set() and schedule.enabled:
            try:
                # Wait for the scheduled time
                sleep_seconds = schedule.interval_minutes * 60
                if stop_flag.wait(timeout=sleep_seconds):
                    break  # Stop flag was set
                
                if not schedule.enabled:
                    break
                
                # Execute the indexing
                self._execute_indexing(schedule)
                
                # Update next run time
                next_run = datetime.now() + timedelta(minutes=schedule.interval_minutes)
                schedule.next_run = next_run.isoformat()
                self.save_schedules()
                
            except Exception as e:
                logging.error(f"Error in scheduled job {schedule_id}: {e}")
                time.sleep(60)  # Wait a minute before retrying
    
    def _execute_indexing(self, schedule: ScheduleConfig):
        """Execute the actual indexing operation"""
        try:
            # Import here to avoid circular imports
            from sharepoint_index_manager import SharePointIndexManager
            from sharepoint_reports import SharePointReports
            
            # Update last run time
            schedule.last_run = datetime.now().isoformat()
            self.save_schedules()
            
            # Create manager and run indexing
            manager = SharePointIndexManager()
            result = manager.index_selected_folders(
                selected_folders=schedule.selected_folders,
                index_name=schedule.index_name,
                file_types=schedule.file_types
            )
            
            # Run auto-purge if enabled and indexing was successful
            if schedule.auto_purge_enabled and result.get('success', False):
                logging.info("Running automatic purge after scheduled indexing...")
                purge_result = self._run_auto_purge(schedule.index_name, schedule.selected_folders)
                result['purge_results'] = purge_result
                
                if purge_result.get("success"):
                    logging.info(f"Auto-purge completed: {purge_result.get('message', 'No message')}")
                else:
                    error_msg = f"Auto-purge failed: {purge_result.get('message', 'Unknown error')}"
                    result.setdefault('errors', []).append(error_msg)
                    logging.error(error_msg)
            
            # Save report
            reports = SharePointReports()
            reports.save_report(
                schedule_name=schedule.name,
                folders=schedule.selected_folders,
                result=result,
                scheduled=True
            )
            
            logging.info(f"Scheduled indexing completed for {schedule.name}: {result}")
            
        except Exception as e:
            logging.error(f"Error executing scheduled indexing for {schedule.name}: {e}")
            # Save error report
            try:
                from sharepoint_reports import SharePointReports
                reports = SharePointReports()
                error_result = {
                    'success': False,
                    'errors': [str(e)],
                    'processed_files': [],
                    'skipped_files': [],
                    'total_processed': 0,
                    'total_chunks': 0
                }
                reports.save_report(
                    schedule_name=schedule.name,
                    folders=schedule.selected_folders,
                    result=error_result,
                    scheduled=True
                )
            except Exception as report_error:
                logging.error(f"Failed to save error report: {report_error}")
    
    def get_schedule_status(self, schedule_id: str) -> Dict[str, Any]:
        """Get status of a schedule"""
        if schedule_id not in self.schedules:
            return {'exists': False}
        
        schedule = self.schedules[schedule_id]
        is_running = (schedule_id in self.running_jobs and 
                     self.running_jobs[schedule_id].is_alive())
        
        return {
            'exists': True,
            'schedule': schedule,
            'is_running': is_running,
            'next_run_in_minutes': self._get_minutes_until_next_run(schedule) if schedule.next_run else None
        }
    
    def _get_minutes_until_next_run(self, schedule: ScheduleConfig) -> Optional[int]:
        """Calculate minutes until next run"""
        if not schedule.next_run:
            return None
        
        try:
            next_run_time = datetime.fromisoformat(schedule.next_run)
            now = datetime.now()
            if next_run_time > now:
                delta = next_run_time - now
                return int(delta.total_seconds() / 60)
            return 0
        except Exception:
            return None
    
    def get_all_schedules(self) -> List[ScheduleConfig]:
        """Get all schedules"""
        return list(self.schedules.values())
    
    def cleanup_finished_jobs(self):
        """Clean up finished background threads"""
        finished_jobs = []
        for schedule_id, thread in self.running_jobs.items():
            if not thread.is_alive():
                finished_jobs.append(schedule_id)
        
        for schedule_id in finished_jobs:
            del self.running_jobs[schedule_id]
            if schedule_id in self.stop_flags:
                del self.stop_flags[schedule_id]
