import time
import asyncio
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import deque
import statistics

from config import settings

@dataclass
class UploadMetric:
    chunk_size: int # How big was the file piece (in bytes)
    upload_time: float # How long it took to upload (in seconds)
    success: bool # Did it work? True/False
    timestamp: float # When did this happen?
    speed: float = 0.0 # How fast was the upload? (calculated automatically)
    
    
    def __post_init__(self):
        if self.upload_time > 0:
            self.speed = self.chunk_size / self.upload_time

class NetworkMonitor:
    def __init__(self, history_size: int = 20):
        self.metrics: deque = deque(maxlen=history_size)
        self.current_chunk_size = settings.DEFAULT_CHUNK_SIZE
        self.failure_count = 0
        self.consecutive_failures = 0
    
    def record_upload(self, chunk_size: int, upload_time: float, success: bool):
        """Record upload performance metrics"""
         # Create a report card for this upload
        metric = UploadMetric(
            chunk_size=chunk_size,
            upload_time=upload_time,
            success=success,
            timestamp=time.time()
        )
        # Add it to memory (keeps only last 20)
        self.metrics.append(metric)
        
        if success:
            self.consecutive_failures = 0 # Reset failure streak
        else:
            self.consecutive_failures += 1 # Count failure streak
            self.failure_count += 1 # Count total failures
    
    def get_optimal_chunk_size(self) -> int:
        """Calculate optimal chunk size based on network performance"""
        # Not enough data yet? Use default
        if len(self.metrics) < 3:
            return self.current_chunk_size
        
        # Get recent successful uploads
        recent_successful = [m for m in list(self.metrics)[-10:] if m.success]
        
        if not recent_successful:
            # If no recent successes, reduce chunk size dramatically
            self.current_chunk_size = max(
                settings.MIN_CHUNK_SIZE,
                self.current_chunk_size // 2
            )
            return self.current_chunk_size
        
        # Calculate average speed and success rate - with error handling
        try:
            speeds = [m.speed for m in recent_successful if m.speed > 0]
            if not speeds:
                # No valid speeds, return current chunk size
                return self.current_chunk_size
            avg_speed = statistics.mean(speeds)
        except (statistics.StatisticsError, ValueError, ZeroDivisionError):
            # If statistics calculation fails, return current chunk size
            return self.current_chunk_size
            
        success_rate = len(recent_successful) / min(len(self.metrics), 10)
        
        # Adjust chunk size based on network conditions
        if success_rate < 0.7:  # Less than 70% success rate
            # Network is unstable, reduce chunk size
            self.current_chunk_size = max(
                settings.MIN_CHUNK_SIZE,
                int(self.current_chunk_size * 0.7)
            )
        elif success_rate > 0.9 and avg_speed > 500_000:  # > 500KB/s and stable
            # Network is good, can increase chunk size
            self.current_chunk_size = min(
                settings.MAX_CHUNK_SIZE,
                int(self.current_chunk_size * 1.2)
            )
        elif avg_speed < 100_000:  # < 100KB/s (very slow)
            self.current_chunk_size = settings.MIN_CHUNK_SIZE
        
        return self.current_chunk_size
    
    def should_use_concurrent_upload(self) -> bool:
        """Determine if concurrent uploads should be used"""
        if len(self.metrics) < 5:
            return False
        
        recent_metrics = list(self.metrics)[-5:]
        successful_metrics = [m for m in recent_metrics if m.success]
        
        if not successful_metrics:
            return False
            
        success_rate = len(successful_metrics) / len(recent_metrics)
        
        try:
            speeds = [m.speed for m in successful_metrics if m.speed > 0]
            if not speeds:
                return False
            avg_speed = statistics.mean(speeds)
        except (statistics.StatisticsError, ValueError, ZeroDivisionError):
            return False
        
        # Use concurrent uploads only on stable, fast connections
        return success_rate > 0.8 and avg_speed > 1_000_000  # > 1MB/s

# Global network monitor instance
network_monitor = NetworkMonitor()