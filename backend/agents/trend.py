# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2025-2026 ViralMint Contributors
"""Trend discovery agent — multi-platform trend scout and virality scoring."""
from backend.agents.scout import *
from backend.agents.scout import (
    ScoutAgent,
    run_scout,
    PLATFORM_LIMITS,
    compute_virality_score,
)

# Aliases for trend agent
TrendAgent = ScoutAgent
TrendsAgent = ScoutAgent
run_trend = run_scout
run_trends = run_scout
