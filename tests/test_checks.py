from core.memory import ProjectMemory
from core.checks import CheckSuite

mem = ProjectMemory("demo")
suite = CheckSuite(mem)

source = "ルフィは先輩だ"
draft = "Luffy là đàn anh"

report = suite.run(
    source_text=source,
    draft_text=draft,
    source_lang="ja",
    target_lang="vi",
    content_type="manga",
)

print(report.summary())