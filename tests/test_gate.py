from core.memory import (
    ProjectMemory,
    Correction,
    CorrectionType,
)
from core.workflow import ApprovalGate


mem = ProjectMemory("demo")
gate = ApprovalGate(mem)

session = gate.create_session(
    chapter_or_doc="ch001",
    source_text="こんにちは先輩",
    draft="Xin chào tiền bối",
    review_note="Glossary mismatch found.",
)

correction = Correction(
    correction_id="corr-001",
    project_id="demo",
    chapter_or_doc="ch001",
    source_lang="ja",
    target_lang="vi",
    correction_type=CorrectionType.TERMINOLOGY,
    original_text="tiền bối",
    corrected_text="senpai",
    note="Use approved fandom term",
)

result = gate.approve(
    session=session,
    final_text="Xin chào senpai",
    corrections=[correction],
)

print("Decision:", session.decision)
print("Final:", session.final_text)
print("Corrections logged:", result.promoted_corrections)

print("\nPending promotions:")
print(gate.get_pending_promotions())