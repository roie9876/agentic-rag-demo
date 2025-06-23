"""
SharePoint Indexing Reports
Handles storage and retrieval of indexing operation reports
"""

import streamlit as st
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
import logging
from dataclasses import dataclass, asdict
import uuid


@dataclass
class IndexingReport:
    """Report for a SharePoint indexing operation"""
    id: str
    schedule_name: str
    timestamp: str
    folders: List[str]
    result: Dict[str, Any]
    scheduled: bool = False
    duration_seconds: Optional[float] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class SharePointReports:
    """Manages SharePoint indexing reports"""
    
    def __init__(self, reports_file: str = "sharepoint_reports.json"):
        self.reports_file = reports_file
        self.reports: Dict[str, IndexingReport] = {}
        self.load_reports()
    
    def load_reports(self):
        """Load reports from file"""
        try:
            if os.path.exists(self.reports_file):
                with open(self.reports_file, 'r') as f:
                    data = json.load(f)
                    for report_id, report_data in data.items():
                        self.reports[report_id] = IndexingReport(**report_data)
        except Exception as e:
            logging.error(f"Error loading reports: {e}")
    
    def save_reports(self):
        """Save reports to file"""
        try:
            data = {}
            for report_id, report in self.reports.items():
                data[report_id] = asdict(report)
            
            with open(self.reports_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.error(f"Error saving reports: {e}")
    
    def save_report(self, schedule_name: str, folders: List[str], result: Dict[str, Any], 
                   scheduled: bool = False, duration_seconds: Optional[float] = None) -> str:
        """Save a new indexing report"""
        report_id = str(uuid.uuid4())
        report = IndexingReport(
            id=report_id,
            schedule_name=schedule_name,
            timestamp=datetime.now().isoformat(),
            folders=folders,
            result=result,
            scheduled=scheduled,
            duration_seconds=duration_seconds
        )
        
        self.reports[report_id] = report
        self.save_reports()
        return report_id
    
    def get_report(self, report_id: str) -> Optional[IndexingReport]:
        """Get a specific report"""
        return self.reports.get(report_id)
    
    def get_all_reports(self, limit: Optional[int] = None) -> List[IndexingReport]:
        """Get all reports, optionally limited"""
        reports = list(self.reports.values())
        # Sort by timestamp (newest first)
        reports.sort(key=lambda r: r.timestamp, reverse=True)
        
        if limit:
            reports = reports[:limit]
        
        return reports
    
    def delete_report(self, report_id: str) -> bool:
        """Delete a report"""
        if report_id in self.reports:
            del self.reports[report_id]
            self.save_reports()
            return True
        return False
    
    def cleanup_old_reports(self, keep_count: int = 100):
        """Keep only the most recent reports"""
        if len(self.reports) <= keep_count:
            return
        
        reports = self.get_all_reports()
        reports_to_keep = reports[:keep_count]
        keep_ids = {report.id for report in reports_to_keep}
        
        # Remove old reports
        old_ids = [report_id for report_id in self.reports.keys() if report_id not in keep_ids]
        for report_id in old_ids:
            del self.reports[report_id]
        
        self.save_reports()
    
    def delete_all_reports(self) -> Dict[str, Any]:
        """Delete all reports"""
        try:
            report_count = len(self.reports)
            self.reports.clear()
            self.save_reports()
            return {
                'success': True,
                'message': f'Successfully deleted {report_count} reports',
                'deleted_count': report_count
            }
        except Exception as e:
            logging.error(f"Error deleting all reports: {e}")
            return {
                'success': False,
                'message': f'Failed to delete reports: {str(e)}',
                'deleted_count': 0
            }
    
    def get_report_summary(self, report: IndexingReport) -> Dict[str, Any]:
        """Get a summary of a report for display"""
        result = report.result
        
        return {
            'id': report.id,
            'name': report.schedule_name,
            'timestamp': report.timestamp,
            'scheduled': report.scheduled,
            'success': result.get('success', False),
            'total_processed': result.get('total_processed', 0),
            'total_chunks': result.get('total_chunks', 0),
            'folders_count': len(report.folders),
            'errors_count': len(result.get('errors', [])),
            'duration': report.duration_seconds
        }
    
    def render_report_list(self, limit: int = 20):
        """Render a list of reports in Streamlit"""
        reports = self.get_all_reports(limit)
        
        if not reports:
            st.info("No indexing reports found.")
            return
        
        st.markdown(f"### 📊 Recent Indexing Reports ({len(reports)} shown)")
        
        for report in reports:
            summary = self.get_report_summary(report)
            
            # Create columns for report display
            col1, col2, col3, col4 = st.columns([3, 2, 2, 1])
            
            with col1:
                status_icon = "✅" if summary['success'] else "❌"
                scheduled_icon = "🕒" if summary['scheduled'] else "👤"
                st.write(f"{status_icon} {scheduled_icon} **{summary['name']}**")
            
            with col2:
                timestamp = datetime.fromisoformat(summary['timestamp'])
                st.write(f"📅 {timestamp.strftime('%Y-%m-%d %H:%M')}")
            
            with col3:
                st.write(f"📁 {summary['folders_count']} folders, {summary['total_chunks']} chunks")
            
            with col4:
                # Action buttons
                if st.button("👁️", key=f"view_{report.id}", help="View details"):
                    st.session_state[f"show_report_{report.id}"] = True
                
                if st.button("🗑️", key=f"delete_{report.id}", help="Delete report"):
                    if self.delete_report(report.id):
                        st.success("Report deleted!")
                        st.rerun()
            
            # Show detailed report if requested
            if st.session_state.get(f"show_report_{report.id}", False):
                with st.expander(f"📋 Report Details: {summary['name']}", expanded=True):
                    self.render_report_details(report)
                    if st.button("Close", key=f"close_{report.id}"):
                        st.session_state[f"show_report_{report.id}"] = False
                        st.rerun()
            
            st.divider()
    
    def render_report_details(self, report: IndexingReport):
        """Render detailed report information"""
        result = report.result
        
        # Basic info
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**📊 Summary**")
            st.write(f"• **Status:** {'✅ Success' if result.get('success', False) else '❌ Failed'}")
            st.write(f"• **Type:** {'🕒 Scheduled' if report.scheduled else '👤 Manual'}")
            st.write(f"• **Timestamp:** {datetime.fromisoformat(report.timestamp).strftime('%Y-%m-%d %H:%M:%S')}")
            if report.duration_seconds:
                st.write(f"• **Duration:** {report.duration_seconds:.1f} seconds")
        
        with col2:
            st.markdown("**📈 Results**")
            st.write(f"• **Folders:** {len(report.folders)}")
            st.write(f"• **Processed Files:** {result.get('total_processed', 0)}")
            st.write(f"• **Total Chunks:** {result.get('total_chunks', 0)}")
            st.write(f"• **Errors:** {len(result.get('errors', []))}")
        
        # Folders processed
        if report.folders:
            st.markdown("**📁 Folders Indexed**")
            for folder in report.folders:
                parts = folder.split('|')
                if len(parts) == 4:
                    display_name = f"{parts[0]}/{parts[1]}/{parts[2]}{parts[3]}"
                    st.write(f"• {display_name}")
                else:
                    st.write(f"• {folder}")
        
        # Processed files
        processed_files = result.get('processed_files', [])
        if processed_files:
            st.markdown(f"**✅ Successfully Processed Files ({len(processed_files)})**")
            for file_info in processed_files[:10]:  # Show first 10
                chunks = file_info.get('chunks', 0)
                method = file_info.get('method', 'unknown')
                folder = file_info.get('folder', '')
                multimodal = file_info.get('multimodal', False)
                multimodal_icon = "🎨" if multimodal else ""
                st.write(f"• **{file_info['name']}** - {chunks} chunks ({method}) {multimodal_icon}")
                if folder:
                    st.write(f"  📁 {folder}")
            
            if len(processed_files) > 10:
                st.write(f"... and {len(processed_files) - 10} more files")
        
        # Skipped files
        skipped_files = result.get('skipped_files', [])
        if skipped_files:
            st.markdown(f"**⚠️ Skipped Files ({len(skipped_files)})**")
            for file_info in skipped_files[:5]:  # Show first 5
                reason = file_info.get('reason', 'Unknown reason')
                folder = file_info.get('folder', '')
                st.write(f"• **{file_info['name']}** - {reason}")
                if folder:
                    st.write(f"  📁 {folder}")
            
            if len(skipped_files) > 5:
                st.write(f"... and {len(skipped_files) - 5} more files")
        
        # Errors
        errors = result.get('errors', [])
        if errors:
            st.markdown(f"**❌ Errors ({len(errors)})**")
            for error in errors:
                st.error(error)
        
        # Raw result data (collapsible)
        with st.expander("🔍 Raw Result Data", expanded=False):
            st.json(result)
    
    def get_reports_stats(self) -> Dict[str, Any]:
        """Get overall statistics about reports"""
        reports = self.get_all_reports()
        
        if not reports:
            return {
                'total_reports': 0,
                'successful_reports': 0,
                'failed_reports': 0,
                'scheduled_reports': 0,
                'manual_reports': 0,
                'total_files_processed': 0,
                'total_chunks_created': 0
            }
        
        successful = sum(1 for r in reports if r.result.get('success', False))
        scheduled = sum(1 for r in reports if r.scheduled)
        total_files = sum(r.result.get('total_processed', 0) for r in reports)
        total_chunks = sum(r.result.get('total_chunks', 0) for r in reports)
        
        return {
            'total_reports': len(reports),
            'successful_reports': successful,
            'failed_reports': len(reports) - successful,
            'scheduled_reports': scheduled,
            'manual_reports': len(reports) - scheduled,
            'total_files_processed': total_files,
            'total_chunks_created': total_chunks
        }
