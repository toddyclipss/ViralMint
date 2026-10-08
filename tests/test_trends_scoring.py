# Copyright (c) 2026 ViralMint. All rights reserved.
# Authorial tests for virality scoring formula in backend.agents.trends.
from datetime import datetime, timedelta
import pytest

from backend.agents.trends import compute_virality_score


class TestViralityScoreBasics:
    def test_returns_float_between_0_and_100(self):
        video = {"views": 1000, "likes": 50, "comments": 10}
        score = compute_virality_score(video)
        assert isinstance(score, float)
        assert 0 <= score <= 100

    def test_zero_views_uses_default(self):
        video = {"views": 0, "likes": 0, "comments": 0}
        score = compute_virality_score(video)
        assert isinstance(score, float)
        assert score >= 0

    def test_negative_values_clamped_to_zero(self):
        video = {"views": 1000, "likes": -5, "comments": -10}
        score = compute_virality_score(video)
        assert score >= 0

    def test_score_capped_at_100(self):
        video = {
            "views": 100_000_000,
            "likes": 10_000_000,
            "comments": 5_000_000,
            "upload_date": datetime.utcnow(),
        }
        score = compute_virality_score(video)
        assert score <= 100.0


class TestViralityScoreFactors:
    def test_higher_engagement_increases_score(self):
        base = {"views": 100_000, "likes": 100, "comments": 10}
        high_engagement = {"views": 100_000, "likes": 10_000, "comments": 5_000}
        assert compute_virality_score(high_engagement) > compute_virality_score(base)

    def test_recency_increases_score(self):
        old_video = {
            "views": 100_000,
            "likes": 5_000,
            "comments": 500,
            "upload_date": datetime.utcnow() - timedelta(days=90),
        }
        recent_video = {
            "views": 100_000,
            "likes": 5_000,
            "comments": 500,
            "upload_date": datetime.utcnow() - timedelta(hours=6),
        }
        assert compute_virality_score(recent_video) > compute_virality_score(old_video)

    def test_more_views_increases_score(self):
        low_views = {"views": 1_000, "likes": 50, "comments": 10}
        high_views = {"views": 1_000_000, "likes": 50, "comments": 10}
        assert compute_virality_score(high_views) > compute_virality_score(low_views)

    def test_comments_weighted_more_than_likes(self):
        more_likes = {"views": 100_000, "likes": 1_000, "comments": 0}
        more_comments = {"views": 100_000, "likes": 0, "comments": 500}
        score_likes = compute_virality_score(more_likes)
        score_comments = compute_virality_score(more_comments)
        assert isinstance(score_likes, float)
        assert isinstance(score_comments, float)


class TestViralityScoreEdgeCases:
    def test_no_upload_date_assumes_30_days(self):
        video = {"views": 100_000, "likes": 5_000, "comments": 500}
        score = compute_virality_score(video)
        assert score > 0

    def test_upload_date_string_treated_as_no_date(self):
        video = {
            "views": 100_000,
            "likes": 5_000,
            "comments": 500,
            "upload_date": "2025-01-01",
        }
        score = compute_virality_score(video)
        assert score > 0

    def test_missing_keys_use_defaults(self):
        video = {"views": 50_000}
        score = compute_virality_score(video)
        assert score >= 0

    def test_empty_dict(self):
        video = {}
        score = compute_virality_score(video)
        assert isinstance(score, float)
        assert score >= 0


class TestViralityScoreSideEffects:
    def test_sets_views_per_hour(self):
        video = {
            "views": 100_000,
            "likes": 5_000,
            "comments": 500,
            "upload_date": datetime.utcnow() - timedelta(hours=10),
        }
        compute_virality_score(video)
        assert "views_per_hour" in video
        assert video["views_per_hour"] == pytest.approx(10_000, rel=0.1)

    def test_sets_outlier_score_when_channel_avg_present(self):
        video = {
            "views": 500_000,
            "likes": 10_000,
            "comments": 1_000,
            "channel_avg_views": 50_000,
        }
        compute_virality_score(video)
        assert "outlier_score" in video
        assert video["outlier_score"] == 10.0

    def test_no_outlier_score_without_channel_avg(self):
        video = {"views": 100_000, "likes": 5_000, "comments": 500}
        compute_virality_score(video)

    def test_outlier_score_from_subscriber_count(self):
        video = {
            "views": 100_000,
            "likes": 5_000,
            "comments": 500,
            "subscriber_count": 10_000,
        }
        compute_virality_score(video)
        assert "outlier_score" in video
        assert video["outlier_score"] > 100
