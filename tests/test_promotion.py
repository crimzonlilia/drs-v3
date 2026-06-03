from core.memory.correction_log import *

log = CorrectionLog("demo")

print("Before:", log.get_pending())

ok = log.promote("corr-001", "glossary")
print("Promoted:", ok)

print("Pending:", log.get_pending())
print(log.summary())