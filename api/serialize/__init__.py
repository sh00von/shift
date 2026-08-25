"""Serialization subpackage — one module per domain."""
from api.serialize._fmt import fmt
from api.serialize.table import table_rows, summary_stats
from api.serialize.charts import chart_data
from api.serialize.diagnostics import diagnostics_data
from api.serialize.forecast import forecast_eval_view
from api.serialize.aln2d import aln2d_summary_rows, aln2d_validation_rows, aln2d_reach_rows

__all__ = [
    "fmt",
    "table_rows",
    "summary_stats",
    "chart_data",
    "diagnostics_data",
    "forecast_eval_view",
    "aln2d_summary_rows",
    "aln2d_validation_rows",
    "aln2d_reach_rows",
]
