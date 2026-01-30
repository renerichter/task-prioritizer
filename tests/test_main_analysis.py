from task_prioritizer.main import get_analysis_text
from task_prioritizer.config import Config


class TestAnalysisText:
    """
    Tests for the deterministic analysis text generator.
    """

    def test_high_impact_low_execution(self):
        text = get_analysis_text(s_impact=0.8, s_execution=0.2, s_urgency=0.0, r_surprise=0.0)
        assert Config.ARCHETYPES['quick_win'] in text

    def test_high_impact_high_execution(self):
        text = get_analysis_text(s_impact=0.8, s_execution=0.8, s_urgency=0.0, r_surprise=0.0)
        assert Config.ARCHETYPES['big_bet'] in text

    def test_low_impact_low_execution(self):
        text = get_analysis_text(s_impact=0.2, s_execution=0.2, s_urgency=0.0, r_surprise=0.0)
        assert Config.ARCHETYPES['filler'] in text

    def test_low_impact_high_execution(self):
        text = get_analysis_text(s_impact=0.2, s_execution=0.8, s_urgency=0.0, r_surprise=0.0)
        assert Config.ARCHETYPES['slog'] in text

    def test_surprise_prefix(self):
        text = get_analysis_text(s_impact=0.8, s_execution=0.2, s_urgency=0.0, r_surprise=0.8)
        assert text.startswith("Scope is unclear (🎁).")
        assert Config.ARCHETYPES['quick_win'] in text

    def test_urgency_suffix(self):
        text = get_analysis_text(s_impact=0.8, s_execution=0.2, s_urgency=0.8, r_surprise=0.0)
        assert text.endswith(" Critical priority.")

    def test_combined_surprise_and_urgency(self):
        text = get_analysis_text(s_impact=0.8, s_execution=0.2, s_urgency=0.8, r_surprise=0.8)
        assert text.startswith("Scope is unclear (🎁).")
        assert "Critical priority." in text
