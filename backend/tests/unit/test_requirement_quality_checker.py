import pytest

from app.agent.quality_checker import RequirementQualityChecker
from app.agent.violation import Violation


class TestAtomicity:
    def test_pass_single_behavior(self):
        desc = "ECU shall read external temperature every 100ms."
        v = RequirementQualityChecker.validate_atomicity(desc, "REQ-001")
        assert len(v) == 0

    def test_fail_multiple_merge_indicators(self):
        desc = "ECU shall read temperature 并且 monitor voltage 同时 log data."
        v = RequirementQualityChecker.validate_atomicity(desc, "REQ-002")
        assert len(v) == 1
        assert v[0].rule_id == "G050-401"
        assert "merge indicators" in v[0].message


class TestCompleteness:
    def test_pass_no_tbd(self):
        desc = "System shall initialize within 100ms."
        v = RequirementQualityChecker.validate_completeness(desc, "REQ-001")
        assert len(v) == 0

    @pytest.mark.parametrize("marker", ["TBD", "待确定", "待定", "后续补充", "待讨论"])
    def test_fail_tbd_markers(self, marker):
        desc = f"System shall {marker} initialize."
        v = RequirementQualityChecker.validate_completeness(desc, "REQ-001")
        assert len(v) == 1
        assert v[0].rule_id == "G050-402"


class TestUnderstandability:
    def test_pass_short_description(self):
        desc = "Module shall detect overvoltage."
        v = RequirementQualityChecker.validate_understandability(desc, "REQ-001")
        assert len(v) == 0

    def test_fail_too_long(self):
        desc = "x" * 501
        v = RequirementQualityChecker.validate_understandability(desc, "REQ-001")
        assert any(viol.rule_id == "G050-403" for viol in v)

    def test_fail_deeply_nested_logic(self):
        desc = "如果 A 并且如果 B 或者如果 C 并且如果 D 那么执行 E。"
        v = RequirementQualityChecker.validate_understandability(desc, "REQ-001")
        assert any(viol.rule_id == "G050-403b" for viol in v)


class TestUnambiguous:
    @pytest.mark.parametrize("word", ["各自的", "适当", "尽量", "相应的", "合理的", "必要时"])
    def test_fail_ambiguous_words(self, word):
        desc = f"System shall {word} handle errors."
        v = RequirementQualityChecker.validate_unambiguous(desc, "REQ-001")
        assert any(viol.rule_id == "G050-413" and word in viol.message for viol in v)

    @pytest.mark.parametrize("sym", ["/", "~"])
    def test_fail_ambiguous_symbols(self, sym):
        desc = f"Range 0{sym}100V."
        v = RequirementQualityChecker.validate_unambiguous(desc, "REQ-001")
        assert any(viol.rule_id == "G050-413b" and sym in viol.message for viol in v)


class TestVerifiable:
    @pytest.mark.parametrize("word", ["立即", "经常", "相当的", "快", "慢", "可能", "左右"])
    def test_fail_weak_words(self, word):
        desc = f"ECU shall {word} respond."
        v = RequirementQualityChecker.validate_verifiable(desc, "REQ-001")
        assert any(viol.rule_id == "G050-414" and word in viol.message for viol in v)

    def test_fail_no_quantifiable_criteria(self):
        desc = "ECU shall initialize safely."
        v = RequirementQualityChecker.validate_verifiable(desc, "REQ-001")
        assert any(viol.rule_id == "G050-414b" for viol in v)

    def test_pass_with_quantifiable(self):
        desc = "ECU shall initialize within 100ms."
        v = RequirementQualityChecker.validate_verifiable(desc, "REQ-001")
        assert not any(viol.rule_id == "G050-414b" for viol in v)

    def test_pass_with_range(self):
        desc = "Voltage range shall be 0~100V."
        v = RequirementQualityChecker.validate_verifiable(desc, "REQ-001")
        # Note: "~" triggers unambiguous warning but quantifiable should pass
        assert not any(viol.rule_id == "G050-414b" for viol in v)

    def test_pass_with_tolerance(self):
        desc = "精度要求为 ±1.5A."
        v = RequirementQualityChecker.validate_verifiable(desc, "REQ-001")
        assert not any(viol.rule_id == "G050-414b" for viol in v)


class TestFeasibility:
    @pytest.mark.parametrize("phrase", ["根据需求", "视情况而定", "尽可能", "在适当的时候"])
    def test_fail_untestable_phrases(self, phrase):
        desc = f"ECU shall {phrase} update firmware."
        v = RequirementQualityChecker.validate_feasibility(desc, "REQ-001")
        assert any(phrase in viol.message for viol in v)
        assert all(viol.severity == "error" for viol in v)


class TestConciseness:
    def test_fail_conclusion_words(self):
        desc = "系统应停止，因此它会 halt。"
        v = RequirementQualityChecker.validate_conciseness(desc, "REQ-001")
        assert any(viol.rule_id == "G050-410" for viol in v)


class TestConsistency:
    def test_pass_unique_ids(self):
        nodes = [
            {"requirement_id": "REQ-001", "description": "A", "children": []},
            {"requirement_id": "REQ-002", "description": "B", "children": []},
        ]
        v = RequirementQualityChecker.validate_consistency(nodes)
        assert len(v) == 0

    def test_fail_duplicate_ids(self):
        nodes = [
            {"requirement_id": "REQ-001", "description": "A", "children": []},
            {"requirement_id": "REQ-001", "description": "B", "children": []},
        ]
        v = RequirementQualityChecker.validate_consistency(nodes)
        assert len(v) == 1
        assert v[0].rule_id == "G050-404"


class TestTraceability:
    def test_pass_valid_id_format(self):
        nodes = [
            {"requirement_id": "SW-REQ-001", "description": "A", "chapter": "3.1", "children": []},
        ]
        v = RequirementQualityChecker.validate_traceability(nodes)
        assert len(v) == 0

    def test_fail_invalid_id_format(self):
        nodes = [
            {"requirement_id": "REQ-1", "description": "A", "children": []},
        ]
        v = RequirementQualityChecker.validate_traceability(nodes)
        assert any(viol.rule_id == "G050-412" for viol in v)

    def test_warn_missing_chapter(self):
        nodes = [
            {"requirement_id": "SW-REQ-001", "description": "A", "children": []},
        ]
        v = RequirementQualityChecker.validate_traceability(nodes)
        assert any(viol.rule_id == "G050-412b" for viol in v)
        assert all(viol.severity == "info" for viol in v if viol.rule_id == "G050-412b")


class TestValidateTree:
    def test_pass_clean_tree(self):
        nodes = [
            {
                "requirement_id": "SW-REQ-001",
                "description": "ECU shall initialize within 100ms.",
                "chapter": "3.1",
                "children": [
                    {
                        "requirement_id": "SW-REQ-001-01",
                        "description": "Register init within 50ms.",
                        "chapter": "3.1.1",
                        "children": [],
                    }
                ],
            }
        ]
        v = RequirementQualityChecker.validate_tree(nodes)
        assert len(v) == 0

    def test_fail_multiple_issues(self):
        nodes = [
            {
                "requirement_id": "SW-REQ-001",
                "description": "ECU 应立即初始化 TBD。",
                "chapter": "3.1",
                "children": [],
            }
        ]
        v = RequirementQualityChecker.validate_tree(nodes)
        # Should catch: weak word "立即", TBD, no quantifiable criteria
        assert any(viol.rule_id == "G050-414" for viol in v)
        assert any(viol.rule_id == "G050-402" for viol in v)
        assert any(viol.rule_id == "G050-414b" for viol in v)

    def test_summary(self):
        nodes = [
            {
                "requirement_id": "SW-REQ-001",
                "description": "System shall immediately TBD handle errors.",
                "children": [],
            }
        ]
        violations = RequirementQualityChecker.validate_tree(nodes)
        summary = RequirementQualityChecker.summarize(violations)
        assert summary["pass"] is False
        assert summary["total"] == len(violations)
        assert summary["error_count"] >= 1
        assert "errors" in summary
        assert "warnings" in summary
        assert "infos" in summary


class TestValidateFlat:
    def test_pass_flat_list(self):
        reqs = [
            {"requirement_id": "SW-REQ-001", "description": "ECU shall init within 100ms."},
            {"requirement_id": "SW-REQ-002", "description": "ECU shall monitor voltage in 0 to 16V range."},
        ]
        v = RequirementQualityChecker.validate_flat(reqs)
        assert len(v) == 0

    def test_fail_duplicate_flat_ids(self):
        reqs = [
            {"requirement_id": "SW-REQ-001", "description": "A"},
            {"requirement_id": "SW-REQ-001", "description": "B"},
        ]
        v = RequirementQualityChecker.validate_flat(reqs)
        assert any(viol.rule_id == "G050-404" for viol in v)


class TestValidateDescription:
    def test_fail_empty_description(self):
        v = RequirementQualityChecker.validate_description("", "REQ-001")
        assert any(viol.rule_id == "G050-000" for viol in v)

    def test_fail_too_short(self):
        v = RequirementQualityChecker.validate_description("init", "REQ-001")
        assert any(viol.rule_id == "G050-000" for viol in v)

    def test_combined_violations(self):
        desc = "ECU 应尽量 立即 处理 TBD 错误 并且 监控电压 同时 记录日志。"
        v = RequirementQualityChecker.validate_description(desc, "REQ-001")
        rule_ids = {viol.rule_id for viol in v}
        assert "G050-413" in rule_ids  # 尽量 = ambiguous
        assert "G050-414" in rule_ids  # 立即 = weak word
        assert "G050-402" in rule_ids  # TBD = incomplete
        assert "G050-401" in rule_ids  # 并且 + 同时 = atomicity warning
        assert "G050-414b" in rule_ids  # no quantifiable criteria
