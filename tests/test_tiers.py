"""Tests for tier definitions and scheduling."""

from two_brain_audit.tiers import DEFAULT_SCHEDULES, Schedule, Tier


class TestTier:
    def test_depth_ordering(self):
        assert Tier.LIGHT.depth < Tier.MEDIUM.depth < Tier.DAILY.depth < Tier.WEEKLY.depth

    def test_weekly_includes_all(self):
        for tier in Tier:
            assert Tier.WEEKLY.includes(tier)

    def test_light_only_includes_self(self):
        assert Tier.LIGHT.includes(Tier.LIGHT)
        assert not Tier.LIGHT.includes(Tier.MEDIUM)

    def test_medium_includes_light(self):
        assert Tier.MEDIUM.includes(Tier.LIGHT)
        assert Tier.MEDIUM.includes(Tier.MEDIUM)
        assert not Tier.MEDIUM.includes(Tier.DAILY)


class TestSchedule:
    def test_daily_matches_3am(self):
        sched = Schedule(tier=Tier.DAILY, hour=3, minute=0)
        assert sched.matches(hour=3, minute=0, weekday=1)
        assert not sched.matches(hour=4, minute=0, weekday=1)

    def test_weekly_matches_sunday_only(self):
        sched = Schedule(tier=Tier.WEEKLY, hour=3, minute=30, weekday=6)
        assert sched.matches(hour=3, minute=30, weekday=6)
        assert not sched.matches(hour=3, minute=30, weekday=0)

    def test_default_schedules_exist(self):
        assert len(DEFAULT_SCHEDULES) == 2
        tiers = {s.tier for s in DEFAULT_SCHEDULES}
        assert Tier.DAILY in tiers
        assert Tier.WEEKLY in tiers
