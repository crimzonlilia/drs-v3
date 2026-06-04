import os
from pathlib import Path

PROMPTS_DIR = Path("config/prompts")

def load_prompt_template(name: str, content_type: str | None = None, default_template: str = "") -> str:
    """
    Load a prompt template from config/prompts/{name}.md.
    If content_type is provided, also load and append the mod from config/prompts/mods/{content_type}.md.
    """
    PROMPTS_DIR.mkdir(parents=True, exist_ok=True)
    
    file_path = PROMPTS_DIR / f"{name}.md"
    
    # 1. Load base template
    if file_path.exists():
        base_content = file_path.read_text(encoding="utf-8").strip()
    else:
        base_content = default_template.strip()
        file_path.write_text(base_content, encoding="utf-8")
        
    # 2. Check for content_type specific modifier
    if content_type:
        mods_dir = PROMPTS_DIR / "mods"
        mods_dir.mkdir(parents=True, exist_ok=True)
        
        mod_path = mods_dir / f"{content_type.lower()}.md"
        if mod_path.exists():
            mod_content = mod_path.read_text(encoding="utf-8").strip()
            base_content = f"{base_content}\n\n[Content Type Mod: {content_type.upper()}]\n{mod_content}"
        else:
            # Auto-generate standard presets so the user has them out-of-the-box
            standard_mods = {
                "manga": "- Since this is manga, keep translations extremely concise to fit inside text bubbles.\n- Use colloquial expressions and dramatic/expressive punctuation appropriate for speech bubbles.",
                "history": "- Since this is a historical document, maintain a formal, objective, academic tone.\n- Respect traditional name formats, historical titles, and geographical spelling conventions.",
                "mythology": "- Since this is mythology/legend, use an epic, archaic, or classical literary tone.\n- Pay attention to divine titles, sacred names, and poetic prose.",
                "scientific": "- Since this is scientific/technical text, use precise, clear terminology.\n- Avoid flowery language and maintain absolute factual accuracy.",
                "general": "Follow general high-quality localization guidelines."
            }
            if content_type.lower() in standard_mods:
                mod_content = standard_mods[content_type.lower()]
                mod_path.write_text(mod_content, encoding="utf-8")
                base_content = f"{base_content}\n\n[Content Type Mod: {content_type.upper()}]\n{mod_content}"
                
    return base_content
