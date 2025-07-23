"""Performance analysis and reporting tools for the rendering system."""

import time
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import defaultdict
import json

from .profiler import profiler


class PerformanceAnalyzer:
    """Analyze and report on rendering performance."""
    
    def __init__(self):
        """Initialize performance analyzer."""
        self.profiler = profiler
        
    def start_session(self, session_name: str = None):
        """Start a new profiling session.
        
        Args:
            session_name: Optional name for the session
        """
        self.profiler.clear()
        self.profiler.enable()
        self.session_name = session_name or f"session_{int(time.time())}"
        self.session_start = time.time()
        
    def end_session(self):
        """End the current profiling session."""
        self.session_end = time.time()
        
    def analyze_bottlenecks(self, min_time: float = 0.001) -> Dict[str, Any]:
        """Analyze performance bottlenecks.
        
        Args:
            min_time: Minimum time threshold for considering operations
            
        Returns:
            Dictionary containing bottleneck analysis
        """
        stats = self.profiler.get_all_stats()
        
        # Filter operations by minimum time
        significant_ops = {
            op: data for op, data in stats.items() 
            if data['total'] >= min_time
        }
        
        # Sort by total time
        sorted_ops = sorted(
            significant_ops.items(), 
            key=lambda x: x[1]['total'], 
            reverse=True
        )
        
        # Categorize operations
        categories = {
            'rendering': [],
            'image_loading': [],
            'entity_processing': [],
            'other': []
        }
        
        for op_name, data in sorted_ops:
            if any(keyword in op_name.lower() for keyword in ['render', 'draw', 'paste']):
                categories['rendering'].append((op_name, data))
            elif any(keyword in op_name.lower() for keyword in ['image', 'resolver', 'load']):
                categories['image_loading'].append((op_name, data))
            elif any(keyword in op_name.lower() for keyword in ['entity', 'grid', 'manager']):
                categories['entity_processing'].append((op_name, data))
            else:
                categories['other'].append((op_name, data))
                
        return {
            'total_operations': len(stats),
            'significant_operations': len(significant_ops),
            'categories': categories,
            'top_bottlenecks': sorted_ops[:10]
        }
        
    def get_image_cache_stats(self) -> Dict[str, Any]:
        """Get image cache performance statistics."""
        stats = self.profiler.get_all_stats()
        counters = self.profiler.get_counters()
        
        image_ops = {
            op: data for op, data in stats.items() 
            if 'ImageResolver' in op or 'image_resolver' in op
        }
        
        total_image_calls = sum(data['count'] for data in image_ops.values())
        total_image_time = sum(data['total'] for data in image_ops.values())
        
        cache_hits = counters.get('image_cache_hits', 0)
        cache_misses = counters.get('image_cache_misses', 0)
        
        hit_rate = cache_hits / (cache_hits + cache_misses) if (cache_hits + cache_misses) > 0 else 0
        
        return {
            'total_image_calls': total_image_calls,
            'total_image_time': total_image_time,
            'avg_time_per_call': total_image_time / total_image_calls if total_image_calls > 0 else 0,
            'cache_hits': cache_hits,
            'cache_misses': cache_misses,
            'cache_hit_rate': hit_rate
        }
        
    def get_entity_rendering_stats(self) -> Dict[str, Any]:
        """Get entity rendering performance statistics."""
        stats = self.profiler.get_all_stats()
        
        entity_render_ops = {
            op: data for op, data in stats.items() 
            if any(keyword in op for keyword in ['_render_', 'render_'])
        }
        
        # Group by render type
        render_types = defaultdict(lambda: {'count': 0, 'total_time': 0, 'operations': []})
        
        for op_name, data in entity_render_ops.items():
            if '_render_entities' in op_name:
                render_type = 'entities'
            elif '_render_trees' in op_name:
                render_type = 'trees'
            elif '_render_resources' in op_name:
                render_type = 'resources'
            elif '_render_shadows' in op_name:
                render_type = 'shadows'
            elif '_render_rails' in op_name:
                render_type = 'rails'
            elif '_render_inventories' in op_name:
                render_type = 'inventories'
            else:
                render_type = 'other'
                
            render_types[render_type]['count'] += data['count']
            render_types[render_type]['total_time'] += data['total']
            render_types[render_type]['operations'].append((op_name, data))
            
        return dict(render_types)
        
    def generate_performance_report(self, 
                                  output_file: Optional[Path] = None,
                                  include_raw_data: bool = False) -> str:
        """Generate a comprehensive performance report.
        
        Args:
            output_file: Optional file to save the report
            include_raw_data: Whether to include raw timing data
            
        Returns:
            Report as a string
        """
        lines = ["=" * 80, "RENDERING PERFORMANCE REPORT", "=" * 80, ""]
        
        # Session info
        if hasattr(self, 'session_start') and hasattr(self, 'session_end'):
            session_duration = self.session_end - self.session_start
            lines.extend([
                f"Session: {getattr(self, 'session_name', 'Unknown')}",
                f"Duration: {session_duration:.3f}s",
                ""
            ])
            
        # Overall statistics
        stats = self.profiler.get_all_stats()
        counters = self.profiler.get_counters()
        
        total_operations = sum(data['count'] for data in stats.values())
        total_time = sum(data['total'] for data in stats.values())
        
        lines.extend([
            "OVERALL STATISTICS:",
            f"Total operations: {total_operations:,}",
            f"Total time: {total_time:.3f}s",
            f"Average time per operation: {total_time/total_operations*1000:.2f}ms" if total_operations > 0 else "N/A",
            ""
        ])
        
        # Bottleneck analysis
        bottlenecks = self.analyze_bottlenecks()
        lines.extend([
            "TOP PERFORMANCE BOTTLENECKS:",
            f"{'Operation':<50} {'Count':<8} {'Total(s)':<10} {'Avg(ms)':<10} {'%Time':<8}",
            "-" * 96
        ])
        
        for op_name, data in bottlenecks['top_bottlenecks']:
            percent_time = (data['total'] / total_time * 100) if total_time > 0 else 0
            lines.append(
                f"{op_name:<50} {data['count']:<8} {data['total']:<10.3f} "
                f"{data['avg']*1000:<10.2f} {percent_time:<8.1f}%"
            )
            
        lines.append("")
        
        # Category breakdown
        lines.extend(["PERFORMANCE BY CATEGORY:", ""])
        for category, ops in bottlenecks['categories'].items():
            if ops:
                category_time = sum(data['total'] for _, data in ops)
                category_percent = (category_time / total_time * 100) if total_time > 0 else 0
                lines.extend([
                    f"{category.upper()}: {category_time:.3f}s ({category_percent:.1f}%)",
                    f"  Operations: {len(ops)}"
                ])
                
                # Show top 3 operations in this category
                for i, (op_name, data) in enumerate(ops[:3]):
                    lines.append(f"    {i+1}. {op_name}: {data['total']:.3f}s ({data['count']} calls)")
                    
                lines.append("")
                
        # Image cache statistics
        cache_stats = self.get_image_cache_stats()
        lines.extend([
            "IMAGE CACHE PERFORMANCE:",
            f"Total image calls: {cache_stats['total_image_calls']:,}",
            f"Total image time: {cache_stats['total_image_time']:.3f}s",
            f"Average time per call: {cache_stats['avg_time_per_call']*1000:.2f}ms",
            f"Cache hit rate: {cache_stats['cache_hit_rate']*100:.1f}%",
            ""
        ])
        
        # Entity rendering breakdown
        entity_stats = self.get_entity_rendering_stats()
        lines.extend(["ENTITY RENDERING BREAKDOWN:", ""])
        for render_type, data in entity_stats.items():
            if data['total_time'] > 0:
                lines.extend([
                    f"{render_type.upper()}:",
                    f"  Total time: {data['total_time']:.3f}s",
                    f"  Operations: {data['count']:,}",
                    f"  Avg per operation: {data['total_time']/data['count']*1000:.2f}ms" if data['count'] > 0 else "  N/A",
                    ""
                ])
                
        # Counter data
        if counters:
            lines.extend(["COUNTERS:", ""])
            for counter, value in sorted(counters.items()):
                lines.append(f"{counter}: {value:,}")
            lines.append("")
            
        # Raw data if requested
        if include_raw_data:
            lines.extend([
                "RAW TIMING DATA:",
                "=" * 50,
                self.profiler.get_report()
            ])
            
        report = "\n".join(lines)
        
        # Save to file if requested
        if output_file:
            with open(output_file, 'w') as f:
                f.write(report)
            lines.extend([
                "",
                f"Report saved to: {output_file}"
            ])
            
        return report
        
    def export_data_for_analysis(self, output_file: Path):
        """Export performance data in JSON format for further analysis.
        
        Args:
            output_file: Path to save the JSON data
        """
        data = {
            'session_info': {
                'name': getattr(self, 'session_name', 'Unknown'),
                'start_time': getattr(self, 'session_start', None),
                'end_time': getattr(self, 'session_end', None),
                'duration': getattr(self, 'session_end', 0) - getattr(self, 'session_start', 0)
            },
            'statistics': self.profiler.get_all_stats(),
            'counters': self.profiler.get_counters(),
            'bottlenecks': self.analyze_bottlenecks(),
            'image_cache_stats': self.get_image_cache_stats(),
            'entity_rendering_stats': self.get_entity_rendering_stats()
        }
        
        with open(output_file, 'w') as f:
            json.dump(data, f, indent=2)


# Convenience functions for easy use
def start_profiling(session_name: str = None) -> PerformanceAnalyzer:
    """Start a profiling session.
    
    Args:
        session_name: Optional name for the session
        
    Returns:
        PerformanceAnalyzer instance
    """
    analyzer = PerformanceAnalyzer()
    analyzer.start_session(session_name)
    return analyzer


def stop_profiling_and_report(analyzer: PerformanceAnalyzer, 
                             output_file: Optional[Path] = None) -> str:
    """Stop profiling and generate a report.
    
    Args:
        analyzer: PerformanceAnalyzer instance from start_profiling()
        output_file: Optional file to save the report
        
    Returns:
        Performance report as string
    """
    analyzer.end_session()
    return analyzer.generate_performance_report(output_file)


# Global instance for convenience
performance_analyzer = PerformanceAnalyzer()