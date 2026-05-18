import pytest

from task_prioritizer.config import Config
from task_prioritizer.main import (
    Colors,
    colorize_output,
    compute_execution,
    compute_impact,
    compute_urgency,
    estimate_time_minutes,
    format_output,
    get_execution_symbol,
    get_impact_symbol,
    get_planned_symbol,
    get_recurrent_symbol,
    get_surprise_symbol,
    get_time_score,
    get_urgency_symbol,
    parse_ratings,
    parse_task,
    prompt_batch_ratings,
    prompt_grouped_batch_ratings,
    run_with_ratings,
)


class TestParseTask:
    """
    Tests for parsing task strings.
    Verifies extraction of existing tags, clean text, and planned time.
    """

    def test_simple_task_no_tags(self):
        tags, text, minutes = parse_task("write a first draft")
        assert tags == ""
        assert text == "write a first draft"
        assert minutes is None

    def test_task_with_single_tag(self):
        tags, text, minutes = parse_task("{P:Web} write a first draft")
        assert tags == "{P:Web}"
        assert text == "write a first draft"
        assert minutes is None

    def test_task_with_time_tag(self):
        tags, text, minutes = parse_task("{p0:45} write a first draft")
        assert tags == "{p0:45}"
        assert text == "write a first draft"
        assert minutes == 45

    def test_task_with_time_tag_hours(self):
        tags, text, minutes = parse_task("{p1:30} longer task")
        assert tags == "{p1:30}"
        assert text == "longer task"
        assert minutes == 90

    def test_task_with_multiple_tags(self):
        tags, text, minutes = parse_task("{p0:45}{P:Web} write a first draft")
        assert tags == "{p0:45}{P:Web}"
        assert text == "write a first draft"
        assert minutes == 45

    def test_task_with_leading_symbols(self):
        tags, text, minutes = parse_task("🗓️{p0:45}{P:Web} write a first draft")
        assert tags == "{p0:45}{P:Web}"
        assert text == "write a first draft"
        assert minutes == 45

    def test_task_with_new_format_symbols(self):
        tags, text, minutes = parse_task("⭐️-🎁🔁-🗓️{p0:45} task")
        assert tags == "{p0:45}"
        assert text == "task"


    def test_task_with_time_in_middle_of_tags(self):
        tags, text, minutes = parse_task("{P:Web}{p2:00}{priority:high} big task")
        assert tags == "{P:Web}{p2:00}{priority:high}"
        assert text == "big task"
        assert minutes == 120

    def test_empty_task(self):
        tags, text, minutes = parse_task("")
        assert tags == ""
        assert text == ""
        assert minutes is None


class TestTimeScore:
    """
    Tests for automatic time-to-score conversion.
    Verifies threshold boundaries exactly as specified.
    """

    def test_quick_task_at_threshold(self):
        assert get_time_score(30) == Config.RATING_MAP['0']

    def test_quick_task_below_threshold(self):
        assert get_time_score(15) == Config.RATING_MAP['0']

    def test_moderate_task_at_low_boundary(self):
        assert get_time_score(31) == Config.RATING_MAP['1']

    def test_moderate_task_at_threshold(self):
        assert get_time_score(90) == Config.RATING_MAP['1']

    def test_substantial_task_at_low_boundary(self):
        assert get_time_score(91) == Config.RATING_MAP['2']

    def test_substantial_task_at_threshold(self):
        assert get_time_score(150) == Config.RATING_MAP['2']

    def test_major_task_above_threshold(self):
        assert get_time_score(151) == Config.RATING_MAP['3']

    def test_very_long_task(self):
        assert get_time_score(480) == Config.RATING_MAP['3']


class TestTimeEstimation:
    """
    Tests for time estimation based on complexity, risk, and surprise.
    """

    def test_minimal_complexity(self):
        estimated = estimate_time_minutes(0.0, 0.0, 0.0)
        assert estimated == 15

    def test_low_complexity(self):
        estimated = estimate_time_minutes(0.3, 0.0, 0.0)
        assert estimated == 45

    def test_medium_complexity(self):
        estimated = estimate_time_minutes(0.6, 0.0, 0.0)
        assert estimated == 90

    def test_high_complexity(self):
        estimated = estimate_time_minutes(1.0, 0.0, 0.0)
        assert estimated == 180

    def test_risk_factor_increases_time(self):
        base = estimate_time_minutes(0.6, 0.0, 0.0)
        with_risk = estimate_time_minutes(0.6, 1.0, 0.0)
        assert with_risk > base
        # 90 * 1.3 = 117 -> round up to 120
        assert with_risk == 120

    def test_surprise_factor_increases_time(self):
        base = estimate_time_minutes(0.6, 0.0, 0.0)
        with_surprise = estimate_time_minutes(0.6, 0.0, 1.0)
        assert with_surprise > base
        # 90 * 1.2 = 108 -> round up to 110
        assert with_surprise == 110

    def test_combined_factors(self):
        estimated = estimate_time_minutes(0.6, 1.0, 1.0)
        # 90 * 1.3 * 1.2 = 140.4 -> round up to 145
        assert estimated == 145


class TestComputeImpact:
    """
    Tests for impact score calculation.
    Verifies weighted combination of Leverage (0.5), Confidence (0.25), and Goals (0.25).
    """

    def test_zero_impact(self):
        score = compute_impact(0.0, 0.0, 0.0)
        assert score == 0.0

    def test_max_impact(self):
        score = compute_impact(1.0, 1.0, 1.0)
        assert score == 1.0

    def test_leverage_only(self):
        score = compute_impact(1.0, 0.0, 0.0)
        assert score == pytest.approx(0.5)

    def test_confidence_only(self):
        score = compute_impact(0.0, 1.0, 0.0)
        assert score == pytest.approx(0.25)

    def test_goals_only(self):
        score = compute_impact(0.0, 0.0, 1.0)
        assert score == pytest.approx(0.25)

    def test_mixed_impact(self):
        score = compute_impact(0.6, 0.3, 0.3)
        expected = 0.6 * 0.5 + 0.3 * 0.25 + 0.3 * 0.25
        assert score == pytest.approx(expected)


class TestComputeUrgency:
    """
    Tests for urgency score calculation.
    Verifies equal weighting of Priority (0.5) and Deadline (0.5).
    """

    def test_zero_urgency(self):
        score = compute_urgency(0.0, 0.0)
        assert score == 0.0

    def test_max_urgency(self):
        score = compute_urgency(1.0, 1.0)
        assert score == 1.0

    def test_priority_only(self):
        score = compute_urgency(1.0, 0.0)
        assert score == pytest.approx(0.5)

    def test_deadline_only(self):
        score = compute_urgency(0.0, 1.0)
        assert score == pytest.approx(0.5)

    def test_mixed_urgency(self):
        score = compute_urgency(0.6, 0.3)
        expected = 0.6 * 0.5 + 0.3 * 0.5
        assert score == pytest.approx(expected)


class TestComputeExecution:
    """
    Tests for execution friction score.
    Verifies weights: Complex (0.4), Time (0.3), Risk (0.2), Fun (0.1).
    """

    def test_zero_friction(self):
        score = compute_execution(0.0, 0.0, 0.0, 0.0)
        assert score == 0.0

    def test_max_friction(self):
        score = compute_execution(1.0, 1.0, 1.0, 1.0)
        assert score == pytest.approx(1.0)

    def test_complex_only(self):
        score = compute_execution(1.0, 0.0, 0.0, 0.0)
        assert score == pytest.approx(0.4)

    def test_time_only(self):
        score = compute_execution(0.0, 1.0, 0.0, 0.0)
        assert score == pytest.approx(0.3)

    def test_risk_only(self):
        score = compute_execution(0.0, 0.0, 1.0, 0.0)
        assert score == pytest.approx(0.2)

    def test_fun_only(self):
        score = compute_execution(0.0, 0.0, 0.0, 1.0)
        assert score == pytest.approx(0.1)

    def test_mixed_friction(self):
        score = compute_execution(0.6, 0.3, 0.6, 0.3)
        expected = 0.6 * 0.4 + 0.3 * 0.3 + 0.6 * 0.2 + 0.3 * 0.1
        assert score == pytest.approx(expected)


class TestImpactSymbol:
    """
    Tests for impact star assignment.
    Boundary: >0.75 → ⭐️⭐️⭐️, >0.50 → ⭐️⭐️, >0.25 → ⭐️, else none.
    """

    def test_three_stars_above_threshold(self):
        sym = get_impact_symbol(0.76)
        assert sym == "⭐️⭐️⭐️"

    def test_three_stars_at_boundary_no_match(self):
        sym = get_impact_symbol(0.75)
        assert sym == "⭐️⭐️"

    def test_two_stars_above_threshold(self):
        sym = get_impact_symbol(0.51)
        assert sym == "⭐️⭐️"

    def test_two_stars_at_boundary_no_match(self):
        sym = get_impact_symbol(0.50)
        assert sym == "⭐️"

    def test_one_star_above_threshold(self):
        sym = get_impact_symbol(0.26)
        assert sym == "⭐️"

    def test_one_star_at_boundary_no_match(self):
        sym = get_impact_symbol(0.25)
        assert sym == ""

    def test_no_stars_below_threshold(self):
        sym = get_impact_symbol(0.20)
        assert sym == ""

    def test_no_stars_zero(self):
        sym = get_impact_symbol(0.0)
        assert sym == ""


class TestUrgencySymbol:
    """
    Tests for urgency symbol assignment.
    Boundary: >=0.5 → 🚨 (urgent), else 🐢 (calm).
    """

    def test_urgent_at_threshold(self):
        sym = get_urgency_symbol(0.5)
        assert sym == "🚨"

    def test_urgent_above_threshold(self):
        sym = get_urgency_symbol(0.8)
        assert sym == "🚨"

    def test_calm_below_threshold(self):
        sym = get_urgency_symbol(0.49)
        assert sym == "🐢"

    def test_calm_zero(self):
        sym = get_urgency_symbol(0.0)
        assert sym == "🐢"


class TestExecutionSymbol:
    """
    Tests for execution symbol assignment.
    Boundary: >=0.5 → 🥵 (hard), else 🍭 (easy).
    """

    def test_hard_at_threshold(self):
        sym = get_execution_symbol(0.5)
        assert sym == "🥵"

    def test_hard_above_threshold(self):
        sym = get_execution_symbol(0.9)
        assert sym == "🥵"

    def test_easy_below_threshold(self):
        sym = get_execution_symbol(0.49)
        assert sym == "🍭"

    def test_easy_zero(self):
        sym = get_execution_symbol(0.0)
        assert sym == "🍭"


class TestSurpriseSymbol:
    """
    Tests for surprise/clarity symbol.
    Boundary: >=0.5 → 🎁 (unclear), else empty.
    """

    def test_surprise_at_threshold(self):
        sym = get_surprise_symbol(0.5)
        assert sym == "🎁"

    def test_surprise_above_threshold(self):
        sym = get_surprise_symbol(1.0)
        assert sym == "🎁"

    def test_no_surprise_below_threshold(self):
        sym = get_surprise_symbol(0.49)
        assert sym == ""

    def test_no_surprise_zero(self):
        sym = get_surprise_symbol(0.0)
        assert sym == ""


class TestPlannedSymbol:
    """
    Tests for planned/spontaneous symbol.
    Boundary: >=0.5 → 🗓️ (planned), else 🎲 (spontaneous).
    """

    def test_planned_at_threshold(self):
        sym = get_planned_symbol(0.5)
        assert sym == "🗓️"

    def test_planned_above_threshold(self):
        sym = get_planned_symbol(1.0)
        assert sym == "🗓️"

    def test_spontaneous_below_threshold(self):
        sym = get_planned_symbol(0.49)
        assert sym == "🎲"

    def test_spontaneous_zero(self):
        sym = get_planned_symbol(0.0)
        assert sym == "🎲"


class TestFormatOutput:
    """
    Tests for final output string formatting.
    Verifies separator logic and tag preservation.
    """

    def test_full_output_with_tags(self):
        result = format_output(
            impact_sym="⭐️⭐️⭐️",
            surprise_sym="🎁",
            planned_sym="🗓️",
            recurrent_sym="🔁",
            tags="{p1:00}{P:Web}",
            text="write a first draft"
        )
        assert result == "⭐️⭐️⭐️-🎁🔁-🗓️{p1:00}{P:Web} write a first draft"

    def test_output_with_stars_no_surprise(self):
        result = format_output(
            impact_sym="⭐️⭐️",
            surprise_sym="",
            planned_sym="🗓️",
            recurrent_sym="",
            tags="{P:Code}",
            text="fix bug"
        )
        assert result == "⭐️⭐️--🗓️{P:Code} fix bug"

    def test_output_with_surprise_no_stars(self):
        result = format_output(
            impact_sym="",
            surprise_sym="🎁",
            planned_sym="🎲",
            recurrent_sym="",
            tags="",
            text="explore idea"
        )
        assert result == "-🎁-🎲 explore idea"

    def test_output_no_stars_no_surprise(self):
        result = format_output(
            impact_sym="",
            surprise_sym="",
            planned_sym="🗓️",
            recurrent_sym="",
            tags="{p0:30}",
            text="quick task"
        )
        assert result == "--🗓️{p0:30} quick task"

    def test_output_no_tags(self):
        result = format_output(
            impact_sym="⭐️",
            surprise_sym="",
            planned_sym="🎲",
            recurrent_sym="",
            tags="",
            text="something"
        )
        assert result == "⭐️--🎲 something"


class TestConfigValidation:
    """
    Tests for configuration validation.
    Ensures weights sum correctly and errors are caught.
    """

    def test_default_config_is_valid(self):
        errors = Config.validate()
        assert errors == []


class TestRatingMapConsistency:
    """
    Tests for rating map consistency.
    Ensures rating and display maps align.
    """

    def test_rating_map_has_four_values(self):
        assert len(Config.RATING_MAP) == 4

    def test_display_map_matches_rating_map(self):
        for key in Config.RATING_MAP:
            assert key in Config.DISPLAY_MAP
            assert Config.DISPLAY_MAP[key] == str(Config.RATING_MAP[key])


class TestEndToEndScenarios:
    """
    Integration tests for realistic user scenarios.
    Combines multiple functions to verify complete flows.
    """

    def test_high_impact_urgent_hard_planned_task(self):
        impact = compute_impact(1.0, 1.0, 1.0)
        urgency = compute_urgency(1.0, 1.0)
        execution = compute_execution(1.0, 1.0, 1.0, 1.0)

        impact_sym = get_impact_symbol(impact)
        urgency_sym = get_urgency_symbol(urgency)
        execution_sym = get_execution_symbol(execution)
        surprise_sym = get_surprise_symbol(0.0)
        planned_sym = get_planned_symbol(1.0)
        recurrent_sym = get_recurrent_symbol(0.0)

        assert impact_sym == "⭐️⭐️⭐️"
        assert urgency_sym == "🚨"
        assert execution_sym == "🥵"
        assert surprise_sym == ""
        assert planned_sym == "🗓️"
        assert recurrent_sym == ""

    def test_low_impact_calm_easy_spontaneous_task(self):
        impact = compute_impact(0.0, 0.0, 0.0)
        urgency = compute_urgency(0.0, 0.0)
        execution = compute_execution(0.0, 0.0, 0.0, 0.0)

        impact_sym = get_impact_symbol(impact)
        urgency_sym = get_urgency_symbol(urgency)
        execution_sym = get_execution_symbol(execution)
        surprise_sym = get_surprise_symbol(0.0)
        planned_sym = get_planned_symbol(0.0)
        recurrent_sym = get_recurrent_symbol(0.0)

        assert impact_sym == ""
        assert urgency_sym == "🐢"
        assert execution_sym == "🍭"
        assert surprise_sym == ""
        assert planned_sym == "🎲"

    def test_phase1_exploration_task_with_surprise(self):
        impact = compute_impact(0.3, 0.3, 0.3)
        urgency = compute_urgency(0.0, 0.0)
        execution = compute_execution(0.6, 0.3, 0.6, 0.0)

        impact_sym = get_impact_symbol(impact)
        urgency_sym = get_urgency_symbol(urgency)
        execution_sym = get_execution_symbol(execution)
        surprise_sym = get_surprise_symbol(1.0)
        planned_sym = get_planned_symbol(0.3)
        recurrent_sym = get_recurrent_symbol(0.0)

        assert impact_sym == "⭐️"
        assert urgency_sym == "🐢"
        assert surprise_sym == "🎁"
        assert planned_sym == "🎲"

        output = format_output(impact_sym, surprise_sym, planned_sym, recurrent_sym, "", "explore new tool")
        assert "🎁" in output
        assert "⭐️-🎁-🎲" in output

    def test_deadline_driven_task(self):
        impact = compute_impact(0.6, 0.3, 0.3)
        urgency = compute_urgency(0.3, 1.0)
        execution = compute_execution(0.3, 0.6, 0.3, 0.0)

        assert urgency >= 0.5
        urgency_sym = get_urgency_symbol(urgency)
        assert urgency_sym == "🚨"


class TestParseRatings:
    """
    Tests for inline ratings parsing (--ratings flag).
    Verifies parsing of comma-separated values and auto-time placeholder.
    """

    def test_valid_ratings_all_zeros(self):
        ratings = parse_ratings("0,0,0,0,0,0,0,0,0,0,0")
        assert ratings is not None
        assert len(ratings) == 12
        assert all(r == 0.0 for r in ratings)

    def test_valid_ratings_all_threes(self):
        ratings = parse_ratings("3,3,3,3,3,3,3,3,3,3,3")
        assert ratings is not None
        assert len(ratings) == 12
        assert all(r == 1.0 for r in ratings[:11])
        assert ratings[11] == 0.0  # Default Rec

    def test_valid_ratings_mixed(self):
        ratings = parse_ratings("3,2,1,0,2,1,0,3,2,1,0")
        assert ratings is not None
        assert len(ratings) == 12
        assert ratings[0] == 1.0
        assert ratings[1] == 0.6

    def test_valid_ratings_with_recurrent(self):
        ratings = parse_ratings("3,2,1,0,2,1,0,3,2,1,0,3")
        assert ratings is not None
        assert len(ratings) == 12
        assert ratings[11] == 1.0

    def test_auto_time_placeholder(self):
        ratings = parse_ratings("3,2,1,0,2,1,_,0,3,2,1", planned_mins=45)
        assert ratings is not None
        assert ratings[6] == Config.RATING_MAP['1']

    def test_auto_time_placeholder_no_planned_time(self):
        ratings = parse_ratings("3,2,1,0,2,1,_,0,3,2,1", planned_mins=None)
        assert ratings is None

    def test_invalid_too_few_values(self):
        ratings = parse_ratings("3,2,1")
        assert ratings is None

    def test_invalid_too_many_values(self):
        ratings = parse_ratings("3,2,1,0,2,1,0,3,2,1,0,1,0")
        assert ratings is None

    def test_invalid_rating_value(self):
        ratings = parse_ratings("3,2,1,0,2,1,5,0,3,2,1")
        assert ratings is None

    def test_ignores_spaces(self):
        ratings = parse_ratings("3, 2, 1, 0, 2, 1, 0, 3, 2, 1, 0")
        assert ratings is not None
        assert len(ratings) == 12


class TestBatchPrompt:
    """
    Tests for batch mode prompt input (legacy single-line).
    Ensures a single-line rating list is parsed correctly.
    """

    def test_prompt_batch_ratings_valid(self, monkeypatch):
        inputs = iter(["3,2,1,0,2,1,_,0,1,0,2,0"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        ratings = prompt_batch_ratings(planned_mins=45)
        assert len(ratings) == 12
        assert ratings[6] == Config.RATING_MAP['1']

    def test_prompt_batch_ratings_retry_on_invalid(self, monkeypatch, capsys):
        inputs = iter(["1,2", "0,0,0,0,0,0,0,0,0,0,0,0"])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        ratings = prompt_batch_ratings(planned_mins=None)
        assert len(ratings) == 12
        out = capsys.readouterr().out
        assert "Use 11 or 12 values" in out


class TestGroupedBatchPrompt:
    """
    Tests for grouped batch mode input.
    Ensures category-by-category input works correctly.
    """

    def test_prompt_grouped_batch_ratings_valid(self, monkeypatch):
        inputs = iter([
            "3,2,1",      # Impact: L,Conf,G
            "2,1",        # Urgency: P,D
            "1,0,2,1",    # Execution: C,T,R,F
            "0,3,0",      # Clarity: S,Pl,Rec
        ])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        ratings = prompt_grouped_batch_ratings(planned_mins=None)
        assert len(ratings) == 12
        assert ratings[0] == 1.0   # L=3
        assert ratings[10] == 1.0  # Pl=3
        assert ratings[11] == 0.0  # Rec=0

    def test_prompt_grouped_batch_with_auto_time(self, monkeypatch):
        inputs = iter([
            "3,2,1",
            "2,1",
            "1,_,2,1",    # T=_ auto-filled
            "0,3,1",      # Clarity: S,Pl,Rec
        ])
        monkeypatch.setattr("builtins.input", lambda _: next(inputs))
        ratings = prompt_grouped_batch_ratings(planned_mins=45)
        assert len(ratings) == 12
        assert ratings[6] == Config.RATING_MAP['1']  # 45 mins → score 1
        assert ratings[11] == 0.3 # Rec=1


class TestRunWithRatings:
    """
    Tests for batch mode execution with inline ratings.
    Verifies end-to-end processing without interactive prompts.
    """

    def test_high_impact_task(self):
        ratings = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        result = run_with_ratings("important task", ratings)
        assert "⭐️⭐️⭐️" in result['output']
        assert result['urgency_sym'] == "🐢"
        assert result['execution_sym'] == "🍭"

    def test_urgent_task(self):
        ratings = [0.0, 0.0, 0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
        result = run_with_ratings("urgent task", ratings)
        assert result['urgency_sym'] == "🚨"

    def test_surprise_task(self):
        ratings = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0]
        result = run_with_ratings("unclear task", ratings)
        assert "🎁" in result['output']
        assert result['has_surprise'] is True

    def test_preserves_tags(self):
        ratings = [1.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0]
        result = run_with_ratings("{p0:45}{P:Code} fix bug", ratings)
        assert "{p0:45}{P:Code}" in result['output']

    def test_result_includes_ratings_dict(self):
        ratings = [1.0, 0.6, 0.3, 0.0, 0.6, 0.3, 0.0, 0.6, 0.3, 0.0, 1.0, 0.3]
        result = run_with_ratings("task", ratings)
        assert 'ratings' in result
        assert result['ratings']['L'] == 1.0
        assert result['ratings']['Conf'] == 0.6
        assert result['ratings']['Pl'] == 1.0
        assert result['ratings']['Rec'] == 0.3

    def test_result_includes_symbols_dict(self):
        ratings = [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 0.0, 1.0, 1.0]
        result = run_with_ratings("task", ratings)
        assert 'symbols' in result
        assert result['symbols']['impact'] == "⭐️⭐️⭐️"
        assert result['symbols']['urgency'] == "🚨"
        assert result['symbols']['planned'] == "🗓️"
        assert result['symbols']['recurrent'] == "🔁"

    def test_estimated_time_returned(self):
        ratings = [0.0, 0.0, 0.0, 0.0, 0.0, 0.6, 0.3, 0.6, 0.0, 0.6, 0.0, 0.0]
        # 90 * 1.0 * 1.0 = 90
        estimated = estimate_time_minutes(0.6, 0.0, 0.0)
        result = run_with_ratings("task", ratings, estimated_mins=estimated)
        assert result['estimated_time_minutes'] == estimated
        # Should now prepend {p1:30} tag (90 mins)
        assert "{p1:30}" in result['output']


class TestColorize:
    """
    Tests for output colorization.
    Verifies color codes are applied to symbols.
    """

    def test_stars_get_gold_color(self):
        result = colorize_output("⭐️⭐️⭐️")
        assert Colors.GOLD in result
        assert "⭐️" in result

    def test_urgent_gets_red_color(self):
        result = colorize_output("🚨")
        assert Colors.RED in result

    def test_calm_gets_green_color(self):
        result = colorize_output("🐢")
        assert Colors.GREEN in result

    def test_surprise_gets_magenta_color(self):
        result = colorize_output("🎁")
        assert Colors.MAGENTA in result

    def test_multiple_symbols_all_colored(self):
        result = colorize_output("⭐️⭐️🎁--🗓️")
        assert Colors.GOLD in result
        assert Colors.MAGENTA in result
        assert Colors.CYAN in result


class TestColorsDisable:
    """
    Tests for color disabling (--no-color flag).
    """

    def test_colors_can_be_disabled(self):
        original_gold = Colors.GOLD
        original_red = Colors.RED
        original_reset = Colors.RESET
        Colors.disable()
        assert Colors.GOLD == ""
        assert Colors.RED == ""
        assert Colors.RESET == ""
        Colors.GOLD = original_gold
        Colors.RED = original_red
        Colors.RESET = original_reset
