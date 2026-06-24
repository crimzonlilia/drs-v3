from __future__ import annotations

import json
from typing import Dict, Any, List, Optional, Tuple
from core.memory import ProjectMemory
from core.checks import CheckSuite, CheckReport
from core.agents.reviewer import Reviewer, ReviewResult
from core.workflow.approval_gate import SESSION_CACHE, ApprovalSession

class AuditResult:
    def __init__(
        self,
        validation_issues: List[Dict[str, Any]],
        editorial_score: Dict[str, float],
        editorial_feedback: List[str],
        audit_report: str
    ):
        self.validation_issues = validation_issues
        self.editorial_score = editorial_score
        self.editorial_feedback = editorial_feedback
        self.audit_report = audit_report

class ConsistencyAuditor:
    """
    ConsistencyAuditor acts as a senior reviewer. It conducts automated
    consistency checks, evaluates editorial quality, and aggregates results.
    """
    
    def __init__(self, memory: ProjectMemory, model: str | None = None):
        self.memory = memory
        self.check_suite = CheckSuite(memory)
        self.reviewer = Reviewer(memory, model=model)

    async def audit(
        self,
        source_text: str,
        current_draft: str,
        source_lang: str,
        target_lang: str,
        content_type: str = "general",
    ) -> AuditResult:
        """
        Main entry point for auditing a translation draft.
        """
        # 1. Run rule-based check suite
        check_report = self.check_suite.run(
            source_text=source_text,
            draft_text=current_draft,
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type
        )

        # 2. Run LLM review pass
        if self.memory.is_empty():
            print("[ConsistencyAuditor] Project memory is empty. Skipping LLM review pass.")
            from core.agents.reviewer import ReviewResult
            review_result = ReviewResult(
                revised_draft=current_draft,
                review_note="No project memory established yet. LLM consistency audit skipped.",
                model="skipped"
            )
        else:
            review_result = await self.reviewer.review(
                source_text=source_text,
                draft=current_draft,
                check_report=check_report,
                source_lang=source_lang,
                target_lang=target_lang,
                content_type=content_type
            )

        # 3. Format validation issues and metrics
        validation_issues = self._format_validation_issues(check_report, current_draft)
        editorial_score, editorial_feedback = self._calculate_editorial_metrics(check_report, review_result.review_note, target_lang=target_lang)

        return AuditResult(
            validation_issues=validation_issues,
            editorial_score=editorial_score,
            editorial_feedback=editorial_feedback,
            audit_report=review_result.review_note
        )

    # ------------------------------------------------------------------ #
    # Facade Tools                                                       #
    # ------------------------------------------------------------------ #

    def run_consistency_checks(self, current_draft: str, session_id: str) -> List[Dict[str, Any]]:
        """
        Validate glossary, entity, continuity, and style. Writes to validation_issues in session.
        """
        session = SESSION_CACHE.get(session_id)
        if not session:
            return []
            
        check_report = self.check_suite.run(
            source_text=session.source_text,
            draft_text=current_draft,
            source_lang=session.source_lang,
            target_lang=session.target_lang
        )
        
        issues = self._format_validation_issues(check_report, current_draft)
        session.validation_issues = issues
        return issues

    def retrieve_relevant_corrections(self, doc_id: str, source_text: str) -> List[Dict[str, Any]]:
        """
        Retrieve style corrections.
        """
        # Return all corrections for this project matching doc_id, or general ones
        all_corrs = self.memory.load_style_corrections()
        relevant = [c for c in all_corrs if c.get("doc_id") == doc_id]
        if not relevant:
            # Fallback to general list
            relevant = all_corrs[:5]
        return relevant

    def evaluate_translation_quality(self, current_draft: str, session_id: str) -> Tuple[Dict[str, float], List[str]]:
        """
        Evaluate fluency, naturalness, tone matching, character voice.
        Updates session metrics.
        """
        session = SESSION_CACHE.get(session_id)
        if not session:
            return {}, []
            
        check_report = self.check_suite.run(
            source_text=session.source_text,
            draft_text=current_draft,
            source_lang=session.source_lang,
            target_lang=session.target_lang
        )
        
        score, feedback = self._calculate_editorial_metrics(check_report, session.audit_report, target_lang=session.target_lang)
        session.editorial_score = score
        session.editorial_feedback = feedback
        return score, feedback

    def generate_audit_summary(self, session_id: str) -> str:
        """
        Summarize validation issues and editorial feedback into a report.
        """
        session = SESSION_CACHE.get(session_id)
        if not session:
            return ""
            
        target_lang = getattr(session, "target_lang", "vi")
        
        if target_lang == "vi":
            report_lines = [
                f"# Báo cáo kiểm định phiên: {session_id}",
                f"Thời gian: {datetime.now().isoformat()}",
                "",
                "## Lỗi chặn duyệt (Blocking Issues):"
            ]
            if session.validation_issues:
                for issue in session.validation_issues:
                    report_lines.append(f"- [{issue.get('violation_type')}] Từ gốc: '{issue.get('source_term')}' -> Lỗi: '{issue.get('violated_term')}' ({issue.get('detail')})")
            else:
                report_lines.append("- Không phát hiện lỗi chặn duyệt.")
                
            report_lines.append("\n## Nhận xét văn phong & Gợi ý (Advisory Feedback):")
            if session.editorial_feedback:
                for fb in session.editorial_feedback:
                    report_lines.append(f"- {fb}")
            else:
                report_lines.append("- Gợi ý văn phong đạt chất lượng.")
        else:
            report_lines = [
                f"# Audit Report for Session: {session_id}",
                f"Time: {datetime.now().isoformat()}",
                "",
                "## Blocking Issues:"
            ]
            if session.validation_issues:
                for issue in session.validation_issues:
                    report_lines.append(f"- [{issue.get('violation_type')}] Original: '{issue.get('source_term')}' -> Error: '{issue.get('violated_term')}' ({issue.get('detail')})")
            else:
                report_lines.append("- No blocking issues detected.")
                
            report_lines.append("\n## Style & Advisory Feedback:")
            if session.editorial_feedback:
                for fb in session.editorial_feedback:
                    report_lines.append(f"- {fb}")
            else:
                report_lines.append("- Style and quality are optimal.")
            
        summary = "\n".join(report_lines)
        session.audit_report = summary
        return summary

    def create_review_package(self, session_id: str) -> Dict[str, Any]:
        """
        Prepares complete package for UI human review.
        """
        session = SESSION_CACHE.get(session_id)
        if not session:
            return {}
        return {
            "session_id": session.session_id,
            "project_id": session.project_id,
            "doc_id": session.doc_id,
            "source_text": session.source_text,
            "current_draft": session.current_draft,
            "validation_issues": session.validation_issues,
            "editorial_score": session.editorial_score,
            "editorial_feedback": session.editorial_feedback,
            "audit_report": session.audit_report,
            "memory_proposals": session.memory_proposals
        }

    # ------------------------------------------------------------------ #
    # Private Helpers                                                    #
    # ------------------------------------------------------------------ #

    def _format_validation_issues(self, report: CheckReport, draft_text: str) -> List[Dict[str, Any]]:
        issues = []
        
        # 1. Terminology flags
        for f in report.term_flags:
            start, end = 0, 0
            if f.found:
                idx = draft_text.find(f.found)
                if idx != -1:
                    start, end = idx, idx + len(f.found)
                
            issues.append({
                "violation_type": "terminology",
                "violated_term": f.expected,
                "source_term": f.source_term,
                "position": [start, end],
                "detail": f"Glossary mismatch: expected '{f.expected}', but found '{f.found or 'nothing'}'",
                "suggestion": f.suggestion
            })

        # 2. Entity flags
        for f in report.entity_flags:
            start, end = 0, 0
            for term_to_find in [f.canonical_name, f.source_name]:
                idx = draft_text.find(term_to_find)
                if idx != -1:
                    start, end = idx, idx + len(term_to_find)
                    break
                    
            issues.append({
                "violation_type": f"entity:{f.violation_type}",
                "violated_term": f.canonical_name,
                "source_term": f.source_name,
                "position": [start, end],
                "detail": f.detail,
                "suggestion": f.suggestion
            })

        # 3. Style flags
        for f in report.style_flags:
            start, end = 0, 0
            issues.append({
                "violation_type": f"style:{f.category}",
                "violated_term": f.rule_id,
                "source_term": "",
                "position": [start, end],
                "detail": f.violation_detail or f.description,
                "suggestion": f.suggestion
            })
            
        return issues

    def _calculate_editorial_metrics(self, report: CheckReport, review_note: str, target_lang: str = "vi") -> Tuple[Dict[str, float], List[str]]:
        from datetime import datetime
        accuracy = max(0.5, 1.0 - len(report.term_flags) * 0.1)
        consistency = max(0.5, 1.0 - len(report.entity_flags) * 0.1)
        fluency = max(0.5, 1.0 - len(report.style_flags) * 0.1)
        
        score = {
            "accuracy": round(accuracy, 2),
            "consistency": round(consistency, 2),
            "fluency": round(fluency, 2)
        }
        
        feedback = []
        if target_lang == "vi":
            if report.term_flags:
                feedback.append(f"Cần chú ý định nghĩa thuật ngữ: {', '.join([f.source_term for f in report.term_flags])}")
            if report.entity_flags:
                feedback.append(f"Lỗi nhất quán nhân vật: {', '.join([f.source_name for f in report.entity_flags])}")
        else:
            if report.term_flags:
                feedback.append(f"Pay attention to terminology definitions: {', '.join([f.source_term for f in report.term_flags])}")
            if report.entity_flags:
                feedback.append(f"Character consistency issues: {', '.join([f.source_name for f in report.entity_flags])}")
        if review_note:
            feedback.append(review_note)
            
        return score, feedback

    async def close(self):
        await self.reviewer.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.close()
from datetime import datetime
