"""
Performance Logger utility module
=================================
Standalone performance logging utility for document processing pipelines.
Tracks timing, bottlenecks, and performance metrics for optimization.
"""
import time
import logging
import os
import json
import tracemalloc
import psutil


class PerformanceLogger:
    """
    Comprehensive performance logging for document processing pipelines.
    Tracks timing, bottlenecks, and performance metrics for optimization.
    """
    
    def __init__(self, file_name: str):
        self.file_name = file_name
        self.stage_times = {}
        self.start_time = time.time()
        self.metadata = {}
        self.api_call_times = {}
        self.memory_usage = {}
        
        # Setup performance logging
        self.perf_logger = logging.getLogger(f"performance.{file_name}")
        if not self.perf_logger.handlers:
            # Create logs directory if it doesn't exist
            os.makedirs("logs/document_processing", exist_ok=True)
            
            # Setup performance file handler
            perf_handler = logging.FileHandler("logs/document_processing/pipeline_performance.log")
            perf_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            perf_handler.setFormatter(perf_formatter)
            self.perf_logger.addHandler(perf_handler)
            self.perf_logger.setLevel(logging.INFO)
            
        self.perf_logger.info(f"[PERF][{self.file_name}][PIPELINE] STARTED")
        
    def log_stage_start(self, stage: str, metadata: dict = None):
        """Start timing a processing stage."""
        self.stage_times[stage] = {'start': time.time()}
        if metadata:
            self.metadata[stage] = metadata
        self.perf_logger.info(f"[PERF][{self.file_name}][{stage}] STARTED")
        
    def log_stage_end(self, stage: str, metadata: dict = None):
        """End timing a processing stage."""
        if stage in self.stage_times:
            elapsed = time.time() - self.stage_times[stage]['start']
            self.stage_times[stage]['duration'] = elapsed
            
            # Combine metadata
            all_metadata = self.metadata.get(stage, {})
            if metadata:
                all_metadata.update(metadata)
                
            metadata_str = f" | {json.dumps(all_metadata)}" if all_metadata else ""
            self.perf_logger.info(f"[PERF][{self.file_name}][{stage}] COMPLETED in {elapsed:.2f}s{metadata_str}")
            
    def log_api_call(self, service: str, operation: str, duration: float, status: str = "success", metadata: dict = None):
        """Log API call performance."""
        if service not in self.api_call_times:
            self.api_call_times[service] = []
            
        call_data = {
            'operation': operation,
            'duration': duration,
            'status': status,
            'timestamp': time.time()
        }
        if metadata:
            call_data.update(metadata)
            
        self.api_call_times[service].append(call_data)
        
        metadata_str = f" | {json.dumps(metadata)}" if metadata else ""
        self.perf_logger.info(f"[API][{self.file_name}][{service}][{operation}] {status.upper()} in {duration:.2f}s{metadata_str}")
        
    def log_bottleneck_analysis(self):
        """Analyze and log performance bottlenecks."""
        if not self.stage_times:
            return
            
        total_time = time.time() - self.start_time
        
        # Calculate stage percentages
        stage_analysis = {}
        for stage, timing in self.stage_times.items():
            if 'duration' in timing:
                percentage = (timing['duration'] / total_time) * 100
                stage_analysis[stage] = {
                    'duration': timing['duration'],
                    'percentage': percentage
                }
                
        # Find bottleneck (longest stage)
        bottleneck = max(stage_analysis.items(), key=lambda x: x[1]['duration']) if stage_analysis else None
        
        if bottleneck:
            stage_name, metrics = bottleneck
            self.perf_logger.warning(
                f"[BOTTLENECK][{self.file_name}] PRIMARY: {stage_name} "
                f"({metrics['duration']:.2f}s, {metrics['percentage']:.1f}% of total time)"
            )
            
        # Log all stage timings
        for stage, metrics in sorted(stage_analysis.items(), key=lambda x: x[1]['duration'], reverse=True):
            self.perf_logger.info(
                f"[TIMING][{self.file_name}][{stage}] {metrics['duration']:.2f}s ({metrics['percentage']:.1f}%)"
            )
            
    def finalize(self):
        """Finalize performance logging and generate summary."""
        total_duration = time.time() - self.start_time
        
        # Log summary
        self.perf_logger.info(f"[PERF][{self.file_name}][PIPELINE] COMPLETED in {total_duration:.2f}s")
        
        # Generate bottleneck analysis
        self.log_bottleneck_analysis()
        
        # API call summary
        for service, calls in self.api_call_times.items():
            total_calls = len(calls)
            total_api_time = sum(call['duration'] for call in calls)
            avg_time = total_api_time / total_calls if total_calls > 0 else 0
            
            self.perf_logger.info(
                f"[API_SUMMARY][{self.file_name}][{service}] "
                f"{total_calls} calls, {total_api_time:.2f}s total, {avg_time:.2f}s avg"
            )
            
    def log_memory_usage(self, stage: str):
        """Log memory usage at specific stage."""
        try:
            process = psutil.Process()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024  # Convert to MB
            
            self.memory_usage[stage] = memory_mb
            self.perf_logger.info(f"[MEMORY][{self.file_name}][{stage}] {memory_mb:.1f}MB")
        except Exception as e:
            self.perf_logger.warning(f"[MEMORY][{self.file_name}][{stage}] Failed to get memory usage: {e}")
            
    def get_stage_duration(self, stage: str) -> float:
        """Get duration of a specific stage."""
        return self.stage_times.get(stage, {}).get('duration', 0.0)
        
    def get_total_duration(self) -> float:
        """Get total pipeline duration so far."""
        return time.time() - self.start_time
        
    def get_performance_summary(self) -> dict:
        """Get comprehensive performance summary."""
        total_duration = self.get_total_duration()
        
        summary = {
            'file_name': self.file_name,
            'total_duration': total_duration,
            'stages': {},
            'api_calls': {},
            'memory_usage': self.memory_usage.copy()
        }
        
        # Stage summary
        for stage, timing in self.stage_times.items():
            if 'duration' in timing:
                summary['stages'][stage] = {
                    'duration': timing['duration'],
                    'percentage': (timing['duration'] / total_duration) * 100,
                    'metadata': self.metadata.get(stage, {})
                }
                
        # API call summary
        for service, calls in self.api_call_times.items():
            if calls:
                total_calls = len(calls)
                total_time = sum(call['duration'] for call in calls)
                avg_time = total_time / total_calls
                success_rate = sum(1 for call in calls if call['status'] == 'success') / total_calls * 100
                
                summary['api_calls'][service] = {
                    'total_calls': total_calls,
                    'total_time': total_time,
                    'average_time': avg_time,
                    'success_rate': success_rate
                }
                
        return summary
