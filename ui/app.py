import sys
from pathlib import Path
import asyncio
import streamlit as st
import uuid
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from core.memory import (
    ProjectMemory,
    Correction,
    CorrectionType,
    Entity,
    StyleRule,
)
from core.workflow import Pipeline, ApprovalGate
from core.agents import FeedbackExtractor


st.set_page_config(
    page_title="DRS v3",
    layout="wide",
)

st.title("DRS v3 — Novel & Manga Translation Hub")
st.caption("Memory-aware localization pipeline with candidate variants & session persistence")


# ---------------------------------------------------
# Session state & Persistence Helpers
# ---------------------------------------------------

# Mock classes to reconstruct PipelineResult from yaml
class MockGeneration:
    def __init__(self, draft):
        self.draft = draft

class MockCheckReport:
    def __init__(self, summary_text, has_issues=False):
        self.summary_text = summary_text
        self.has_issues = has_issues
    def summary(self):
        return self.summary_text

class MockReview:
    def __init__(self, note):
        self.review_note = note

class MockSession:
    def __init__(self, session_id, source_text, draft):
        self.session_id = session_id
        self.source_text = source_text
        self.draft = draft
        self.corrections = []
        self.decision = None
        self.decided_at = ""

class MockPipelineResult:
    def __init__(self, session_id, source_text, draft, check_summary, review_note):
        self.session = MockSession(session_id, source_text, draft)
        self.generation = MockGeneration(draft)
        self.check_report = MockCheckReport(check_summary)
        self.review = MockReview(review_note)
        self.final_text = draft
        self.approved = True

def save_session_state():
    if not st.session_state.get("has_active_session"):
        return
    session_dir = Path("workspace/sessions")
    session_dir.mkdir(parents=True, exist_ok=True)
    session_file = session_dir / f"{st.session_state.active_project_id}_ui_demo.yaml"
    
    data = {
        "project_id": st.session_state.active_project_id,
        "source_text": st.session_state.active_source_text,
        "candidates": st.session_state.active_candidates,
        "selected_index": st.session_state.active_selected_index,
        "draft_text": st.session_state.active_draft_text,
        "edited_text": st.session_state.active_edited_text,
        "check_report": st.session_state.active_check_report,
        "review_note": st.session_state.active_review_note,
        "session_corrections": st.session_state.session_corrections,
        "has_active_session": True
    }
    session_file.write_text(yaml.dump(data, allow_unicode=True), encoding="utf-8")

def load_session_state(proj_id):
    session_file = Path("workspace/sessions") / f"{proj_id}_ui_demo.yaml"
    if session_file.exists():
        try:
            data = yaml.safe_load(session_file.read_text(encoding="utf-8"))
            if data and data.get("has_active_session"):
                st.session_state.active_project_id = data["project_id"]
                st.session_state.active_source_text = data["source_text"]
                st.session_state.active_candidates = data["candidates"]
                st.session_state.active_selected_index = data["selected_index"]
                st.session_state.active_draft_text = data["draft_text"]
                st.session_state.active_edited_text = data.get("edited_text", data["draft_text"])
                st.session_state.active_check_report = data["check_report"]
                st.session_state.active_review_note = data["review_note"]
                st.session_state.session_corrections = data["session_corrections"]
                st.session_state.has_active_session = True
                
                # Reconstruct result object for UI compatibility
                st.session_state.result = MockPipelineResult(
                    session_id=f"{proj_id}-ui-resumed",
                    source_text=data["source_text"],
                    draft=data["draft_text"],
                    check_summary=data["check_report"],
                    review_note=data["review_note"]
                )
                return True
        except Exception as e:
            st.sidebar.error(f"Error loading session: {e}")
    return False

def clear_session_state(proj_id):
    session_file = Path("workspace/sessions") / f"{proj_id}_ui_demo.yaml"
    if session_file.exists():
        try:
            session_file.unlink()
        except Exception:
            pass
    st.session_state.has_active_session = False
    st.session_state.active_source_text = ""
    st.session_state.active_candidates = []
    st.session_state.active_selected_index = 0
    st.session_state.active_draft_text = ""
    st.session_state.active_edited_text = ""
    st.session_state.active_check_report = ""
    st.session_state.active_review_note = ""
    st.session_state.session_corrections = []
    st.session_state.result = None

# Initialize session state variables
if "has_active_session" not in st.session_state:
    st.session_state.has_active_session = False
    st.session_state.active_project_id = ""
    st.session_state.active_source_text = ""
    st.session_state.active_candidates = []
    st.session_state.active_selected_index = 0
    st.session_state.active_draft_text = ""
    st.session_state.active_edited_text = ""
    st.session_state.active_check_report = ""
    st.session_state.active_review_note = ""
    st.session_state.session_corrections = []
    st.session_state.result = None

# Initialize Manga Workspace variables
if "manga_blocks" not in st.session_state:
    st.session_state.manga_blocks = []
    st.session_state.manga_image_bytes = None
    st.session_state.manga_translated_image = None


# ---------------------------------------------------
# Sidebar
# ---------------------------------------------------

st.sidebar.header("Project")

import yaml

def get_existing_projects():
    projects_dir = Path("projects")
    projects = []
    if projects_dir.exists():
        for d in projects_dir.iterdir():
            if d.is_dir() and not d.name.startswith("."):
                projects.append(d.name)
    if "demo_project" not in projects:
        projects.append("demo_project")
    return sorted(projects)

def load_project_config(proj_id: str):
    config_path = Path("projects") / proj_id / "project.yaml"
    if config_path.exists():
        try:
            return yaml.safe_load(config_path.read_text(encoding="utf-8"))
        except Exception:
            pass
    return None

existing_projects = get_existing_projects()
selected_project = st.sidebar.selectbox(
    "Select Project",
    existing_projects
)

project_id = selected_project
config = load_project_config(project_id)

if config:
    proj_source_lang = config.get("source_lang", "ja")
    proj_target_lang = config.get("target_lang", "vi")
    proj_content_type = config.get("content_type", "novel")
else:
    proj_source_lang = "ja"
    proj_target_lang = "vi"
    proj_content_type = "novel"
    
st.sidebar.info(
    f"**Source**: {proj_source_lang.upper()}  \n"
    f"**Target**: {proj_target_lang.upper()}  \n"
    f"**Type**: {proj_content_type.capitalize()}"
)

source_lang = proj_source_lang
target_lang = proj_target_lang
content_type = proj_content_type

# Dedicated Expander to Create New Project
with st.sidebar.expander("➕ Create New Project", expanded=False):
    new_project_id = st.text_input("New Project ID (slug)", "my-new-project", key="new_proj_id").strip()
    new_source = st.selectbox("Source Language", ["ja", "en", "ko"], index=0, key="new_proj_src")
    new_target = st.selectbox("Target Language", ["vi", "en"], index=0, key="new_proj_tgt")
    new_content = st.selectbox("Content Type", ["manga", "novel", "fanfic", "general"], index=1, key="new_proj_type")
    new_tone = st.text_area("Initial Tone Note", "Dịch văn phong tự nhiên, trôi chảy", key="new_proj_tone")
    
    if st.button("Create Project", key="btn_create_project"):
        if new_project_id:
            # Create project directory
            proj_dir = Path("projects") / new_project_id / "chapters"
            proj_dir.mkdir(parents=True, exist_ok=True)
            
            # Save configuration
            config_path = Path("projects") / new_project_id / "project.yaml"
            config_data = {
                "project_id": new_project_id,
                "source_lang": new_source,
                "target_lang": new_target,
                "content_type": new_content,
                "tone_note": new_tone,
            }
            config_path.write_text(yaml.dump(config_data, allow_unicode=True), encoding="utf-8")
            
            # Initialize ProjectMemory and Style Profile
            new_mem = ProjectMemory(new_project_id)
            new_mem.style.init_profile(
                source_lang=new_source,
                target_lang=new_target,
                content_type=new_content,
                tone_note=new_tone
            )
            
            st.success(f"Project '{new_project_id}' created!")
            st.rerun()
        else:
            st.error("Project ID is required.")
        


# Mode indicator on the main page
if content_type == "manga":
    st.warning("🎨 **Manga mode active**: Visual translation tools (OCR, image inpainting) are currently under development. Running text-based translation for manga script dialogue.")
else:
    st.success("📖 **Novel translation mode active**: Multi-stage text-to-text pipeline with rule consistency checks, LLM reviewer feedback, and candidate variant selection.")

mem = ProjectMemory(project_id)

# Try to load session if not already loaded or if project changed
if st.session_state.active_project_id != project_id:
    st.session_state.active_project_id = project_id
    loaded = load_session_state(project_id)
    if not loaded:
        st.session_state.has_active_session = False
        st.session_state.active_source_text = ""
        st.session_state.active_candidates = []
        st.session_state.active_selected_index = 0
        st.session_state.active_draft_text = ""
        st.session_state.active_check_report = ""
        st.session_state.active_review_note = ""
        st.session_state.session_corrections = []
        st.session_state.result = None

# Auto-initialize style profile in UI if missing
if mem.style.profile is None:
    mem.style.init_profile(
        source_lang=source_lang,
        target_lang=target_lang,
        content_type=content_type,
        tone_note="Dịch sát nghĩa, văn phong tự nhiên"
    )

st.sidebar.subheader("Project Style Settings")
current_tone_note = mem.style.profile.tone_note if mem.style.profile else ""
tone_note_input = st.sidebar.text_area(
    "Overall Tone / Style Note",
    value=current_tone_note,
    help="e.g., 'dịch thô', 'dịch lãng mạn', 'văn phong hài hước'"
)
if tone_note_input != current_tone_note:
    mem.style.update_tone_note(tone_note_input)

if st.sidebar.button("Refine Style with AI"):
    if tone_note_input.strip():
        with st.spinner("AI is refining style directive..."):
            from core.agents.feedback_extractor import FeedbackExtractor
            extractor = FeedbackExtractor(mem)
            async def _refine():
                return await extractor.refine_tone(tone_note_input)
            try:
                refined = asyncio.run(_refine())
                asyncio.run(extractor.close())
                mem.style.update_tone_note(refined)
                st.sidebar.success("Style note refined!")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Refinement failed: {e}")

st.sidebar.divider()
st.sidebar.subheader("Fandom Memory Auto-Seed")
fandom_input = st.sidebar.text_input(
    "Fandom/Franchise Name",
    placeholder="e.g. Fate/Grand Order, One Piece",
    help="AI will automatically research and pre-populate Glossary, Entities, and Style guidelines for this fandom."
)
if st.sidebar.button("🔍 Auto-Seed Memory"):
    if fandom_input.strip():
        with st.spinner(f"AI is researching and seeding '{fandom_input}' memory..."):
            from core.agents.fandom_researcher import FandomResearcher
            async def _seed():
                researcher = FandomResearcher(mem)
                res = await researcher.seed_project_memory(
                    fandom_input,
                    source_lang=source_lang,
                    target_lang=target_lang
                )
                await researcher.close()
                return res
            try:
                res = asyncio.run(_seed())
                st.sidebar.success(
                    f"Seeded: {res['glossary_count']} glossary, "
                    f"{res['entities_count']} entities, "
                    f"{res['style_count']} style rules!"
                )
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"Seeding failed: {e}")

gate = ApprovalGate(mem)

pending = gate.get_pending_promotions()

st.sidebar.subheader("Translation Settings")
num_candidates = st.sidebar.number_input(
    "Draft Candidates Count",
    min_value=1,
    max_value=5,
    value=1,
    help="Generate multiple draft variants to select from"
)

st.sidebar.divider()

st.sidebar.subheader("Memory Status")

st.sidebar.write(
    f"Glossary: {len(mem.glossary)} entries"
)

st.sidebar.write(
    f"Entities: {len(mem.entities)} entries"
)

pending_count = sum(
    len(v)
    for v in pending.values()
)

st.sidebar.write(
    f"Pending Corrections: {pending_count}"
)



# ---------------------------------------------------
# Manga Translation Workspace
# ---------------------------------------------------
if content_type == "manga":
    st.title("🎨 Manga Translation Workspace")
    st.write(
        "Upload a manga page image (raw Japanese). AI will run OCR to detect speech bubbles, "
        "classify bubble types, translate text to Vietnamese using glossary context, and typeset them."
    )

    # Initialize manga-specific state variables if not already initialized
    if "manga_evaluation" not in st.session_state:
        st.session_state.manga_evaluation = None

    uploaded_file = st.file_uploader(
        "Upload Manga Page (PNG, JPG, JPEG)",
        type=["png", "jpg", "jpeg"]
    )

    if uploaded_file is not None:
        image_bytes = uploaded_file.read()
        
        # Reset if the image changes
        if st.session_state.manga_image_bytes != image_bytes:
            st.session_state.manga_image_bytes = image_bytes
            st.session_state.manga_blocks = []
            st.session_state.manga_translated_image = None
            st.session_state.manga_evaluation = None

        st.markdown("### ⚙️ Workflow Settings")
        manga_mode = st.radio(
            "Translation & Rendering Flow Mode",
            [
                "Review & Approve Translations First (Safe Mode)",
                "Direct Fast Translation (Burn Text Immediately)"
            ],
            index=0
        )

        col_action1, col_action2 = st.columns(2)
        with col_action1:
            if st.button("Run Manga DRS (OCR + Translate)", type="primary"):
                with st.spinner("AI is analyzing layout, OCRing text blocks, and translating..."):
                    from core.agents.layout_translator import LayoutTranslator, LayoutTextBlock
                    from core.workflow.image_renderer import render_image_layout_page
                    
                    async def _translate_manga():
                        async with LayoutTranslator(mem) as translator:
                            return await translator.translate_page(
                                image_bytes,
                                source_lang=source_lang,
                                target_lang=target_lang
                            )
                    try:
                        blocks = asyncio.run(_translate_manga())
                        st.session_state.manga_blocks = blocks
                        st.session_state.manga_evaluation = None
                        
                        if "Fast" in manga_mode:
                            # Generate initial rendered page immediately
                            translated_bytes = render_image_layout_page(image_bytes, blocks)
                            st.session_state.manga_translated_image = translated_bytes
                            st.success(f"Detected and typeset {len(blocks)} speech bubbles directly!")
                        else:
                            st.session_state.manga_translated_image = None
                            st.success(f"Detected and translated {len(blocks)} speech bubbles. Review below before rendering!")
                    except Exception as e:
                        st.error(f"Manga translation failed: {e}")

        # If we have translation results, display the interactive workbench
        if st.session_state.manga_blocks:
            st.write("---")
            
            # Left: Editing Pane | Right: Rendering Pane
            col_review, col_preview = st.columns([1, 1])
            
            with col_review:
                st.subheader("✍️ Speech Bubble Review")
                st.write("Edit translations and select bubble types to customize font styles.")
                
                # Render inputs for each text bubble
                updated_blocks = []
                for i, block in enumerate(st.session_state.manga_blocks):
                    st.markdown(f"**Bubble {i+1}** (Position: {block.box})")
                    
                    # Original text read-only
                    st.text_input(
                        f"Original Text ({source_lang.upper()})",
                        value=block.source_text,
                        disabled=True,
                        key=f"manga_ja_{block.block_id}"
                    )
                    
                    # Editable translation
                    edited_tgt = st.text_area(
                        f"Translation ({target_lang.upper()})",
                        value=block.translated_text,
                        key=f"manga_vi_{block.block_id}",
                        height=80
                    )
                    
                    # Select bubble type for font choice
                    b_types = ["normal", "thought", "scream", "narration"]
                    current_type = block.bubble_type if block.bubble_type in b_types else "normal"
                    edited_type = st.selectbox(
                        "Bubble Font Type",
                        b_types,
                        index=b_types.index(current_type),
                        key=f"manga_type_{block.block_id}"
                    )
                    
                    from core.agents.layout_translator import LayoutTextBlock
                    updated_blocks.append(
                        LayoutTextBlock(
                            block_id=block.block_id,
                            box=block.box,
                            source_text=block.source_text,
                            translated_text=edited_tgt,
                            bubble_type=edited_type
                        )
                    )
                    st.write("")
                
                if st.button("🔄 Update & Re-render Page"):
                    from core.workflow.image_renderer import render_image_layout_page
                    st.session_state.manga_blocks = updated_blocks
                    with st.spinner("Re-typesetting Vietnamese text..."):
                        translated_bytes = render_image_layout_page(
                            st.session_state.manga_image_bytes,
                            updated_blocks
                        )
                        st.session_state.manga_translated_image = translated_bytes
                        st.success("Re-rendered successfully!")
                        st.rerun()

            with col_preview:
                st.subheader("🖼️ Visual Preview")
                
                preview_mode = st.radio(
                    "Display Mode",
                    ["Translated Page", "Original Page"],
                    horizontal=True
                )
                
                if preview_mode == "Original Page":
                    st.image(st.session_state.manga_image_bytes, use_container_width=True)
                else:
                    if st.session_state.manga_translated_image:
                        st.image(st.session_state.manga_translated_image, use_container_width=True)
                        st.download_button(
                            "📥 Download Typeset Page",
                            data=st.session_state.manga_translated_image,
                            file_name="translated_page.png",
                            mime="image/png"
                        )
                        
                        # Add Visual QA Review Action
                        st.markdown("---")
                        st.subheader("🤖 Visual QA Evaluation")
                        if st.button("🔍 Run Typesetting Review"):
                            with st.spinner("AI is analyzing image layout and checking for overflow..."):
                                from core.agents.layout_translator import LayoutTranslator
                                async def _eval_manga():
                                    async with LayoutTranslator(mem) as translator:
                                        return await translator.evaluate_rendered_page(
                                            st.session_state.manga_image_bytes,
                                            st.session_state.manga_translated_image,
                                            st.session_state.manga_blocks
                                        )
                                try:
                                    eval_result = asyncio.run(_eval_manga())
                                    st.session_state.manga_evaluation = eval_result
                                except Exception as e:
                                    st.error(f"QA Evaluation failed: {e}")
                                    
                        if st.session_state.manga_evaluation:
                            st.info(st.session_state.manga_evaluation)
                            
                    else:
                        st.info("Please review translations and click 'Update & Re-render Page' or select 'Direct Fast Translation' to generate the typeset view.")
    else:
        st.info("Please upload a manga page image to begin.")
        
    st.stop()


# ---------------------------------------------------
# Step 1 — Source
# ---------------------------------------------------

# Session Resume Banner
if st.session_state.has_active_session:
    st.info(f"🔄 Resumed active translation session for project **{st.session_state.active_project_id}**.")
    if st.button("Discard and Start Over"):
        clear_session_state(project_id)
        st.rerun()

with st.expander(
    "Step 1 — Source",
    expanded=True,
):

    source_text = st.text_area(
        "Source Text",
        value=st.session_state.active_source_text,
        height=180,
    )


async def generate_candidates(source_txt, count):
    from core.agents.candidate_generator import CandidateGenerator
    async with CandidateGenerator(mem) as generator:
        tasks = []
        for _ in range(count):
            temp = 0.7 if count > 1 else None
            tasks.append(
                generator.generate(
                    source_text=source_txt,
                    source_lang=source_lang,
                    target_lang=target_lang,
                    content_type=content_type,
                    temperature=temp
                )
            )
        results = await asyncio.gather(*tasks)
        return [r.draft for r in results]

async def evaluate_draft(draft_text):
    from core.checks import CheckSuite
    check_suite = CheckSuite(mem)
    check_report = check_suite.run(
        source_text=st.session_state.active_source_text,
        draft_text=draft_text,
        source_lang=source_lang,
        target_lang=target_lang,
        content_type=content_type,
    )
    
    from core.agents.reviewer import Reviewer
    async with Reviewer(mem) as reviewer:
        review_result = await reviewer.review(
            source_text=st.session_state.active_source_text,
            draft=draft_text,
            check_report=check_report,
            source_lang=source_lang,
            target_lang=target_lang,
            content_type=content_type,
        )
    return check_report.summary(), review_result.review_note

def extract_and_log_corrections_bg(mem, source_lang, target_lang, content_type, feedback_val, edited_val):
    if feedback_val.strip() or edited_val.strip() != st.session_state.active_draft_text.strip():
        from core.agents.feedback_extractor import FeedbackExtractor
        
        async def _extract():
            async with FeedbackExtractor(mem) as extractor:
                return await extractor.extract(
                    source_text=st.session_state.active_source_text,
                    draft_text=st.session_state.active_draft_text,
                    final_text=edited_val,
                    feedback_text=feedback_val,
                )
        try:
            extracted = asyncio.run(_extract())
            for item in extracted:
                # De-duplicate
                st.session_state.session_corrections = [
                    c for c in st.session_state.session_corrections
                    if not (
                        (c["source_term"] and item.source_term and c["source_term"] == item.source_term) or
                        (not c["source_term"] and not item.source_term and c["original_text"] == item.original_text)
                    )
                ]
                st.session_state.session_corrections.append({
                    "source_term": item.source_term,
                    "original_text": item.original_text,
                    "corrected_text": item.corrected_text,
                    "correction_type": item.correction_type,
                    "note": item.note,
                })
            save_session_state()
        except Exception as e:
            print(f"Background extraction failed: {e}")

if st.button("Run DRS"):
    if not source_text.strip():
        st.warning("Enter source text.")
    else:
        with st.spinner("Generating translation candidates..."):
            st.session_state.active_source_text = source_text
            st.session_state.active_project_id = project_id
            
            candidates = asyncio.run(generate_candidates(source_text, num_candidates))
            st.session_state.active_candidates = candidates
            st.session_state.active_selected_index = 0
            
            # Evaluate the first candidate
            st.info("Running Step 1 (Consistency Checks) and Step 2 (AI Review) on Candidate 1...")
            check_summary, review_note = asyncio.run(evaluate_draft(candidates[0]))
            
            st.session_state.active_draft_text = candidates[0]
            st.session_state.active_edited_text = candidates[0]
            st.session_state.active_check_report = check_summary
            st.session_state.active_review_note = review_note
            st.session_state.session_corrections = []
            st.session_state.has_active_session = True
            
            # Reconstruct result object for UI compatibility
            st.session_state.result = MockPipelineResult(
                session_id=f"{project_id}-ui-{int(time.time())}",
                source_text=source_text,
                draft=candidates[0],
                check_summary=check_summary,
                review_note=review_note
            )
            
            save_session_state()
            st.rerun()


# ---------------------------------------------------
# Step 2 — Draft
# ---------------------------------------------------

if st.session_state.result:

    result = st.session_state.result

    # Display candidate selector if we have multiple candidates
    if len(st.session_state.active_candidates) > 1:
        st.markdown("### 🎭 Candidate Selection")
        selected_idx = st.radio(
            "Compare and select the best candidate draft to proceed:",
            range(len(st.session_state.active_candidates)),
            index=st.session_state.active_selected_index,
            format_func=lambda i: f"Variant {i+1}: {st.session_state.active_candidates[i][:80]}...",
            key="candidate_selector_radio"
        )
        
        if selected_idx != st.session_state.active_selected_index:
            st.session_state.active_selected_index = selected_idx
            with st.spinner(f"Re-evaluating Candidate {selected_idx + 1}..."):
                draft_to_eval = st.session_state.active_candidates[selected_idx]
                check_summary, review_note = asyncio.run(evaluate_draft(draft_to_eval))
                st.session_state.active_draft_text = draft_to_eval
                st.session_state.active_edited_text = draft_to_eval
                st.session_state.active_check_report = check_summary
                st.session_state.active_review_note = review_note
                
                # Reconstruct result object
                st.session_state.result = MockPipelineResult(
                    session_id=result.session.session_id,
                    source_text=st.session_state.active_source_text,
                    draft=draft_to_eval,
                    check_summary=check_summary,
                    review_note=review_note
                )
                save_session_state()
                st.rerun()

    with st.expander(
        "Step 2 — AI Draft & Evaluations",
        expanded=True,
    ):
        st.caption("AI Output & Analysis")
        
        # Display evaluations side-by-side or tabs
        eval_tab1, eval_tab2 = st.tabs(["🔍 Step 1: Consistency Check Report", "🤖 Step 2: LLM Review Note"])
        with eval_tab1:
            st.code(st.session_state.active_check_report, language="markdown")
        with eval_tab2:
            st.info(st.session_state.active_review_note or "No review notes generated.")

        st.subheader("Edit Translation Draft")
        edited_text = st.text_area(
            "Editable Draft",
            value=st.session_state.active_edited_text,
            height=260,
            key="editable_draft_text_area"
        )
        if edited_text != st.session_state.active_edited_text:
            st.session_state.active_edited_text = edited_text
            save_session_state()


    # ---------------------------------------------------
    # Step 3 — Human Review & Feedback
    # ---------------------------------------------------

    with st.expander(
        "Step 3 — Human Review and Feedback",
        expanded=True,
    ):
        st.subheader("AI feedback loop & revision")
        st.write(
            "Enter your feedback comments below (e.g. 'Change tiền bối to senpai, character Luffy not Lupin'). "
            "AI will automatically extract corrections and rewrite the translation draft based on your instruction."
        )

        feedback_input = st.text_area(
            "Feedback Comments (Chat)",
            height=100,
            placeholder="Type feedback here..."
        )

        if st.button("Revise Draft with AI Feedback"):
            if feedback_input.strip() or edited_text.strip() != st.session_state.active_draft_text.strip():
                with st.spinner("AI is analyzing feedback, extracting corrections, and revising translation..."):
                    # 1. Background extraction of corrections
                    extract_and_log_corrections_bg(mem, source_lang, target_lang, content_type, feedback_input, edited_text)
                    
                    # 2. Build feedback value (fallback to manual edits note if empty)
                    actual_feedback = feedback_input
                    if not actual_feedback.strip() and edited_text.strip() != st.session_state.active_draft_text.strip():
                        actual_feedback = f"Sử dụng cách diễn đạt trong bản hiệu đính của tôi làm chuẩn: '{edited_text}'"

                    # 3. Run revision with AI feedback and session corrections
                    from core.agents.candidate_generator import CandidateGenerator
                    async def _revise():
                        async with CandidateGenerator(mem) as generator:
                            return await generator.revise(
                                source_text=st.session_state.active_source_text,
                                previous_draft=st.session_state.active_draft_text,
                                feedback=actual_feedback,
                                source_lang=source_lang,
                                target_lang=target_lang,
                                content_type=content_type,
                                session_corrections=st.session_state.session_corrections,
                            )
                    try:
                        rev_result = asyncio.run(_revise())
                        check_summary, review_note = asyncio.run(evaluate_draft(rev_result.draft))
                        
                        # Append revised draft to candidates list
                        st.session_state.active_candidates.append(rev_result.draft)
                        st.session_state.active_selected_index = len(st.session_state.active_candidates) - 1
                        
                        st.session_state.active_draft_text = rev_result.draft
                        st.session_state.active_edited_text = rev_result.draft
                        st.session_state.active_check_report = check_summary
                        st.session_state.active_review_note = review_note
                        
                        # Reconstruct result object
                        st.session_state.result = MockPipelineResult(
                            session_id=result.session.session_id,
                            source_text=st.session_state.active_source_text,
                            draft=rev_result.draft,
                            check_summary=check_summary,
                            review_note=review_note
                        )
                        save_session_state()
                        st.success("Draft revised and re-evaluated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Revision failed: {e}")
            else:
                st.warning("Please provide feedback comments or edit the draft to revise.")

        st.write("---")
        with st.expander("Manually Add Correction", expanded=False):
            m_src = st.text_input("Source Term (Original language)")
            m_orig = st.text_input("AI Draft (Incorrect translation)")
            m_corr = st.text_input("Corrected Translation")
            m_type = st.selectbox(
                "Correction Type",
                ["terminology", "entity", "style", "factual", "other"],
                key="manual_corr_type"
            )
            m_note = st.text_input("Note (Optional)", key="manual_corr_note")
            
            if st.button("Add Manual Correction"):
                if m_corr.strip():
                    # De-duplicate
                    st.session_state.session_corrections = [
                        c for c in st.session_state.session_corrections
                        if not (
                            (c["source_term"] and m_src.strip() and c["source_term"] == m_src.strip()) or
                            (not c["source_term"] and not m_src.strip() and c["original_text"] == m_orig.strip())
                        )
                    ]
                    st.session_state.session_corrections.append({
                        "source_term": m_src.strip(),
                        "original_text": m_orig.strip(),
                        "corrected_text": m_corr.strip(),
                        "correction_type": m_type,
                        "note": m_note.strip(),
                    })
                    st.success("Manual correction added.")
                    st.rerun()
                else:
                    st.warning("Corrected Translation is required.")

        # Display and edit session corrections
        if st.session_state.session_corrections:
            st.markdown("#### Logged Corrections for this Session")
            
            # Form to manually add custom correction if needed
            to_remove = []
            for i, corr in enumerate(st.session_state.session_corrections):
                c_col1, c_col2, c_col3, c_col4, c_col5 = st.columns([2, 2, 2, 2, 1])
                with c_col1:
                    corr["source_term"] = st.text_input(
                        "Source Term", value=corr["source_term"], key=f"sess_src_{i}"
                    )
                with c_col2:
                    corr["original_text"] = st.text_input(
                        "Original Draft", value=corr["original_text"], key=f"sess_orig_{i}"
                    )
                with c_col3:
                    corr["corrected_text"] = st.text_input(
                        "Corrected", value=corr["corrected_text"], key=f"sess_corr_{i}"
                    )
                with c_col4:
                    corr["correction_type"] = st.selectbox(
                        "Type",
                        ["terminology", "entity", "style", "factual", "other"],
                        index=["terminology", "entity", "style", "factual", "other"].index(corr["correction_type"]),
                        key=f"sess_type_{i}"
                    )
                with c_col5:
                    st.write("") # formatting spacing
                    if st.button("Delete", key=f"sess_del_{i}"):
                        to_remove.append(i)
            
            # Remove deleted corrections
            if to_remove:
                for idx in sorted(to_remove, reverse=True):
                    st.session_state.session_corrections.pop(idx)
                st.rerun()

        st.divider()

        # Approve and save draft
        if st.button("Approve and Save Draft"):
            with st.spinner("AI is analyzing edits, extracting corrections, and saving..."):
                # 1. Background extraction of corrections
                extract_and_log_corrections_bg(mem, source_lang, target_lang, content_type, feedback_input, edited_text)
                
                # 2. Build Correction list
                corrections = []
                for corr in st.session_state.session_corrections:
                    corrections.append(
                        Correction(
                            correction_id=str(uuid.uuid4())[:8],
                            project_id=project_id,
                            chapter_or_doc="ui_demo",
                            source_lang=source_lang,
                            target_lang=target_lang,
                            correction_type=CorrectionType(corr["correction_type"]),
                            source_term=corr["source_term"],
                            original_text=corr["original_text"],
                            corrected_text=corr["corrected_text"],
                            note=corr.get("note", "UI correction"),
                        )
                    )

                promotion = gate.approve(
                    session=result.session,
                    final_text=edited_text,
                    corrections=corrections,
                )

            # Manually write human-approved output files to projects directory
            try:
                chapter_path = Path("projects") / project_id / "chapters" / "ui_demo"
                chapter_path.mkdir(parents=True, exist_ok=True)
                
                # approved.md
                (chapter_path / "approved.md").write_text(edited_text, encoding="utf-8")
                
                # draft.md
                (chapter_path / "draft.md").write_text(result.generation.draft, encoding="utf-8")
                
                # review_log.md
                log_lines = [
                    f"# Review Log — ui_demo",
                    f"Run: {result.session.session_id}",
                    f"Date: {result.session.decided_at}",
                    f"Decision: {result.session.decision}",
                    "",
                    "## Check Report",
                    result.check_report.summary(),
                    "",
                    "## Review Note",
                    result.review.review_note,
                ]
                if corrections:
                    log_lines += ["", "## Corrections Logged"]
                    for c in corrections:
                        log_lines.append(
                            f"- [{c.correction_type.value}] '{c.original_text}' → '{c.corrected_text}'"
                        )
                (chapter_path / "review_log.md").write_text("\n".join(log_lines), encoding="utf-8")
                
                st.success("Draft approved and saved successfully (written to projects/).")
            except Exception as e:
                st.error(f"Failed to write output files: {e}")

            clear_session_state(project_id)
            st.rerun()


# ---------------------------------------------------
# Step 4 — Memory Management Dashboard
# ---------------------------------------------------

with st.expander(
    "📚 Step 4 — Project Memory Management",
    expanded=True,
):
    st.write(
        "Here you can view, edit, or delete any glossary terms, entities, and style guidelines "
        "stored in this project's persistent memory."
    )

    tab_glos, tab_ent, tab_styl = st.tabs([
        f"📖 Glossary ({len(mem.glossary)} entries)",
        f"👥 Entities ({len(mem.entities)} entries)",
        f"🎨 Style Rules ({len(mem.style.profile.rules) if mem.style.profile else 0} entries)"
    ])

    with tab_glos:
        st.subheader("📚 Active Glossary Entries")
        glos_entries = mem.glossary.get_all(source_lang=source_lang, target_lang=target_lang)
        if not glos_entries:
            st.caption("No glossary entries for this language pair yet.")
        else:
            for idx, entry in enumerate(glos_entries):
                col_g1, col_g2, col_g3, col_g4 = st.columns([2, 3, 3, 2])
                with col_g1:
                    st.write(f"**{entry.source_term}**")
                with col_g2:
                    new_tgt = st.text_input(
                        "Translation",
                        value=entry.target_term,
                        key=f"glos_tgt_val_{idx}",
                        label_visibility="collapsed"
                    )
                with col_g3:
                    new_note = st.text_input(
                        "Context / Note",
                        value=entry.context_note or "",
                        key=f"glos_note_val_{idx}",
                        label_visibility="collapsed"
                    )
                with col_g4:
                    col_sub1, col_sub2 = st.columns(2)
                    with col_sub1:
                        if st.button("💾", key=f"glos_save_btn_{idx}", help="Save changes"):
                            entry.target_term = new_tgt
                            entry.context_note = new_note
                            mem.glossary.add_entry(entry)
                            st.success("Saved!")
                            st.rerun()
                    with col_sub2:
                        if st.button("🗑️", key=f"glos_del_btn_{idx}", help="Delete entry"):
                            mem.glossary.remove_entry(entry.source_term, entry.source_lang, entry.target_lang)
                            st.warning("Deleted!")
                            st.rerun()

    with tab_ent:
        st.subheader("👥 Active Entities")
        entities = mem.entities.get_all(source_lang=source_lang, target_lang=target_lang)
        if not entities:
            st.caption("No entities registered yet.")
        else:
            for idx, ent in enumerate(entities):
                col_e1, col_e2, col_e3, col_e4 = st.columns([2, 3, 3, 2])
                with col_e1:
                    st.write(f"**{ent.source_name}** ({ent.entity_type})")
                with col_e2:
                    new_canon = st.text_input(
                        "Canonical Name",
                        value=ent.canonical_name,
                        key=f"ent_canon_val_{idx}",
                        label_visibility="collapsed"
                    )
                with col_e3:
                    new_pronouns = st.text_input(
                        "Pronouns / Note",
                        value=ent.pronouns or ent.notes or "",
                        key=f"ent_note_val_{idx}",
                        label_visibility="collapsed"
                    )
                with col_e4:
                    col_sub1, col_sub2 = st.columns(2)
                    with col_sub1:
                        if st.button("💾", key=f"ent_save_btn_{idx}", help="Save changes"):
                            ent.canonical_name = new_canon
                            ent.pronouns = new_pronouns
                            mem.entities.add_entity(ent)
                            st.success("Saved!")
                            st.rerun()
                    with col_sub2:
                        if st.button("🗑️", key=f"ent_del_btn_{idx}", help="Delete entity"):
                            mem.entities.remove_entity(ent.entity_id)
                            st.warning("Deleted!")
                            st.rerun()

    with tab_styl:
        st.subheader("🎨 Style Guide Rules")
        style_rules = mem.style.get_rules()
        if not style_rules:
            st.caption("No style rules defined yet.")
        else:
            for idx, rule in enumerate(style_rules):
                col_s1, col_s2, col_s3 = st.columns([3, 5, 2])
                with col_s1:
                    st.write(f"**Category:** {rule.category}")
                    if rule.example_before:
                        st.caption(f"✗: {rule.example_before} -> ✓: {rule.example_after}")
                with col_s2:
                    new_desc = st.text_input(
                        "Rule Description",
                        value=rule.description,
                        key=f"style_desc_val_{idx}",
                        label_visibility="collapsed"
                    )
                with col_s3:
                    col_sub1, col_sub2 = st.columns(2)
                    with col_sub1:
                        if st.button("💾", key=f"style_save_btn_{idx}", help="Save changes"):
                            rule.description = new_desc
                            mem.style.add_rule(rule)
                            st.success("Saved!")
                            st.rerun()
                    with col_sub2:
                        if st.button("🗑️", key=f"style_del_btn_{idx}", help="Delete rule"):
                            mem.style.remove_rule(rule.rule_id)
                            st.warning("Deleted!")
                            st.rerun()