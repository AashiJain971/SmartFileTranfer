"""
AI-Powered Network Predictor
Adaptive network quality prediction using statistical analysis and anomaly detection.
No ML libraries required - uses pure statistics and trend analysis.
"""

import numpy as np
from collections import deque
from datetime import datetime
from typing import Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class AdaptiveNetworkPredictor:
    """
    Adaptive network predictor using hybrid statistical + rule-based approach.
    
    Handles:
    - Anomaly detection (power cuts, sudden slowdowns)
    - Trend prediction (gradual degradation/improvement)
    - Time-of-day patterns (hourly averages)
    """
    
    def __init__(self):
        # Short-term history for real-time adaptation
        self.recent_history = deque(maxlen=50)  # Last 50 measurements
        
        # Long-term patterns (hourly averages)
        self.hourly_patterns: Dict[int, Dict[str, float]] = {}
        
        # Anomaly detection thresholds
        self.anomaly_threshold = 2.5  # Standard deviations
        
        # Confidence scoring
        self.prediction_confidence = 1.0
    
    def add_measurement(self, latency: float, bandwidth: float, timestamp: Optional[datetime] = None):
        """Record a network measurement"""
        if timestamp is None:
            timestamp = datetime.now()
            
        measurement = {
            'latency': latency,
            'bandwidth': bandwidth,
            'timestamp': timestamp,
            'hour': timestamp.hour
        }
        
        self.recent_history.append(measurement)
        self._update_hourly_patterns(measurement)
        
        logger.debug(f"Recorded measurement: latency={latency:.2f}ms, bandwidth={bandwidth:.2f}Mbps")
    
    def predict_next_quality(self, lookahead_seconds: int = 10) -> Dict[str, Any]:
        """
        Predict network quality 5-10 seconds ahead
        
        Returns:
            dict: {
                'predicted_quality': 'degrading'|'improving'|'stable',
                'confidence': 0.0-1.0,
                'suggested_action': 'reduce_chunk'|'increase_chunk'|'maintain',
                'reason': str explaining the prediction,
                'is_anomaly': bool
            }
        """
        # ✅ Reduced requirement: 3 measurements instead of 10 for faster startup
        if len(self.recent_history) < 3:
            return self._fallback_prediction("Insufficient data for prediction (need at least 3 measurements)")
            
        # === STEP 1: Check for anomalies (rare events) ===
        anomaly_detected, anomaly_reason = self._detect_anomaly()
        
        if anomaly_detected:
            # IMMEDIATE DEFENSIVE ACTION for unexpected events
            logger.warning(f"🚨 Anomaly detected: {anomaly_reason}")
            return {
                'predicted_quality': 'degrading',
                'confidence': 0.95,  # High confidence in anomaly detection
                'suggested_action': 'reduce_chunk',
                'reason': f"⚠️ Anomaly: {anomaly_reason}",
                'is_anomaly': True
            }
        
        # === STEP 2: Trend analysis (works for gradual changes) ===
        trend = self._analyze_trend()
        
        # === STEP 3: Time-of-day prediction (recurring patterns) ===
        hourly_prediction = self._predict_from_hourly_pattern()
        
        # === STEP 4: Combine predictions with confidence weighting ===
        final_prediction = self._combine_predictions(trend, hourly_prediction)
        
        logger.info(f"🤖 AI Prediction: {final_prediction['predicted_quality']} (confidence: {final_prediction['confidence']:.2f})")
        
        return final_prediction
    
    def _detect_anomaly(self) -> Tuple[bool, Optional[str]]:
        """
        Detect rare events (power cuts, sudden slowdowns)
        
        Returns:
            (bool, str): (is_anomaly, reason)
        """
        if len(self.recent_history) < 5:
            return False, None
            
        recent = list(self.recent_history)[-5:]
        
        # Calculate recent statistics
        recent_latencies = [m['latency'] for m in recent]
        recent_bandwidths = [m['bandwidth'] for m in recent]
        
        # Get baseline from longer history (if available)
        if len(self.recent_history) > 20:
            baseline = list(self.recent_history)[-20:-5]
            baseline_latencies = [m['latency'] for m in baseline]
            baseline_bandwidths = [m['bandwidth'] for m in baseline]
            
            baseline_lat_mean = np.mean(baseline_latencies)
            baseline_lat_std = np.std(baseline_latencies)
            baseline_bw_mean = np.mean(baseline_bandwidths)
            baseline_bw_std = np.std(baseline_bandwidths)
        else:
            # Use current stats as baseline
            baseline_lat_mean = np.mean(recent_latencies)
            baseline_lat_std = np.std(recent_latencies) or 1
            baseline_bw_mean = np.mean(recent_bandwidths)
            baseline_bw_std = np.std(recent_bandwidths) or 1
        
        # === Anomaly Detection Rules ===
        
        # 1. Sudden latency spike (power cut, WiFi disconnect)
        if recent_latencies[-1] > baseline_lat_mean + (self.anomaly_threshold * baseline_lat_std):
            spike_magnitude = (recent_latencies[-1] - baseline_lat_mean) / baseline_lat_mean * 100
            return True, f"Latency spike +{spike_magnitude:.0f}% (possible connection issue)"
        
        # 2. Bandwidth collapse (network congestion, ISP throttling)
        if recent_bandwidths[-1] < baseline_bw_mean - (self.anomaly_threshold * baseline_bw_std):
            drop_magnitude = (baseline_bw_mean - recent_bandwidths[-1]) / baseline_bw_mean * 100
            return True, f"Bandwidth drop -{drop_magnitude:.0f}% (possible congestion)"
        
        # 3. Rapid oscillation (unstable connection)
        latency_changes = np.diff(recent_latencies)
        if len(latency_changes) > 0 and np.std(latency_changes) > baseline_lat_std * 1.5:
            return True, "Unstable connection (high variance)"
        
        # 4. Connection timeout pattern (repeated failures)
        timeout_threshold = 5000  # 5 seconds
        timeout_count = sum(1 for lat in recent_latencies if lat > timeout_threshold)
        if timeout_count >= 2:
            return True, f"Multiple timeouts detected ({timeout_count}/5 measurements)"
        
        return False, None
    
    def _analyze_trend(self) -> Dict[str, Any]:
        """
        Analyze short-term trend (gradual degradation/improvement)
        Works with as few as 3 measurements
        """
        # ✅ Use all available data (min 3, max 10)
        num_points = min(10, len(self.recent_history))
        recent = list(self.recent_history)[-num_points:]
        
        latencies = [m['latency'] for m in recent]
        
        # Linear regression slope
        x = np.arange(len(latencies))
        slope = np.polyfit(x, latencies, 1)[0]
        
        # ✅ Adjust thresholds based on data points (more lenient with fewer points)
        threshold = 5 if num_points >= 7 else 8  # Higher threshold for fewer points
        
        # Categorize trend
        if slope > threshold:  # Latency increasing
            quality = 'degrading'
            confidence = min(abs(slope) / 20, 0.9)  # Cap at 0.9, not 1.0
        elif slope < -threshold:  # Latency decreasing
            quality = 'improving'
            confidence = min(abs(slope) / 20, 0.9)
        else:
            quality = 'stable'
            # ✅ Higher confidence for stable predictions (most common case)
            confidence = 0.75 if num_points >= 5 else 0.70
            
        return {
            'quality': quality,
            'confidence': confidence,
            'slope': slope
        }
    
    def _predict_from_hourly_pattern(self) -> Optional[Dict[str, Any]]:
        """Predict based on time-of-day patterns"""
        current_hour = datetime.now().hour
        next_hour = (current_hour + 1) % 24
        
        # Check if we have enough historical data for this hour
        if current_hour not in self.hourly_patterns or next_hour not in self.hourly_patterns:
            return None  # Not enough data
        
        current_avg_lat = self.hourly_patterns[current_hour]['avg_latency']
        next_avg_lat = self.hourly_patterns[next_hour]['avg_latency']
        
        # Predict transition
        if next_avg_lat > current_avg_lat * 1.2:
            return {
                'quality': 'degrading',
                'confidence': 0.6,  # Lower confidence for hourly predictions
                'reason': f'Historical pattern: {next_hour}:00 typically slower'
            }
        elif next_avg_lat < current_avg_lat * 0.8:
            return {
                'quality': 'improving',
                'confidence': 0.6,
                'reason': f'Historical pattern: {next_hour}:00 typically faster'
            }
        
        return {
            'quality': 'stable',
            'confidence': 0.5,
            'reason': 'No significant hourly pattern'
        }
    
    def _combine_predictions(self, trend: Dict[str, Any], hourly: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Combine multiple prediction sources with confidence weighting"""
        
        # If no hourly data, rely purely on trend
        if hourly is None:
            return {
                'predicted_quality': trend['quality'],
                'confidence': trend['confidence'],
                'suggested_action': self._quality_to_action(trend['quality']),
                'reason': f"Trend-based: slope={trend['slope']:.2f}ms/measurement",
                'is_anomaly': False
            }
        
        # Weight by confidence
        trend_weight = trend['confidence']
        hourly_weight = hourly['confidence']
        total_weight = trend_weight + hourly_weight
        
        # Majority vote with weighted confidence
        predictions = [
            (trend['quality'], trend_weight),
            (hourly['quality'], hourly_weight)
        ]
        
        # Count weighted votes
        quality_scores = {'degrading': 0, 'improving': 0, 'stable': 0}
        for quality, weight in predictions:
            quality_scores[quality] += weight
        
        # Pick winner
        predicted_quality = max(quality_scores, key=quality_scores.get)
        combined_confidence = quality_scores[predicted_quality] / total_weight
        
        return {
            'predicted_quality': predicted_quality,
            'confidence': combined_confidence,
            'suggested_action': self._quality_to_action(predicted_quality),
            'reason': f"Combined: Trend ({trend['quality']}) + Hourly ({hourly.get('reason', 'N/A')})",
            'is_anomaly': False
        }
    
    def _quality_to_action(self, quality: str) -> str:
        """Convert quality prediction to chunk size action"""
        if quality == 'degrading':
            return 'reduce_chunk'
        elif quality == 'improving':
            return 'increase_chunk'
        else:
            return 'maintain'
    
    def _fallback_prediction(self, reason: str) -> Dict[str, Any]:
        """
        Smart fallback when prediction is uncertain
        Still analyzes current state instead of blind 0.3 confidence
        """
        # Even with limited data, analyze what we have
        if len(self.recent_history) >= 1:
            recent = list(self.recent_history)[-min(3, len(self.recent_history)):]
            avg_latency = np.mean([m['latency'] for m in recent])
            
            # Make educated guess based on current network state
            if avg_latency < 100:
                quality = 'stable'
                confidence = 0.75  # Good network, fairly confident
                action_reason = f"Good latency (~{avg_latency:.0f}ms) - safe to proceed"
            elif avg_latency < 300:
                quality = 'stable'
                confidence = 0.70  # Decent network
                action_reason = f"Moderate latency (~{avg_latency:.0f}ms) - stable operation"
            else:
                quality = 'degrading'
                confidence = 0.65  # Poor network, be cautious
                action_reason = f"High latency (~{avg_latency:.0f}ms) - recommending smaller chunks"
            
            return {
                'predicted_quality': quality,
                'confidence': confidence,
                'suggested_action': self._quality_to_action(quality),
                'reason': action_reason,
                'is_anomaly': False
            }
        
        # True fallback: no data at all
        return {
            'predicted_quality': 'stable',
            'confidence': 0.5,  # Neutral confidence, not 0.3
            'suggested_action': 'maintain',
            'reason': f"No data available - using safe defaults",
            'is_anomaly': False
        }
    
    def _update_hourly_patterns(self, measurement: Dict[str, Any]):
        """Update long-term hourly averages"""
        hour = measurement['hour']
        
        if hour not in self.hourly_patterns:
            self.hourly_patterns[hour] = {
                'count': 0,
                'sum_latency': 0,
                'sum_bandwidth': 0,
                'avg_latency': 0,
                'avg_bandwidth': 0
            }
        
        pattern = self.hourly_patterns[hour]
        pattern['count'] += 1
        pattern['sum_latency'] += measurement['latency']
        pattern['sum_bandwidth'] += measurement['bandwidth']
        pattern['avg_latency'] = pattern['sum_latency'] / pattern['count']
        pattern['avg_bandwidth'] = pattern['sum_bandwidth'] / pattern['count']
