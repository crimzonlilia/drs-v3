import os
import sys
import asyncio
import base64
import hmac
import hashlib
from datetime import datetime
import yaml

from core.utils.db import init_db, execute_query
from core.utils.r2 import write_text

def get_password_hash(password: str) -> str:
    salt = os.urandom(16)
    iterations = 100000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

async def seed():
    # Set sys.stdout to handle UTF-8 print
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

    # Clean old records and folders
    print("Cleaning up old database records...")
    await execute_query("DELETE FROM segments")
    await execute_query("DELETE FROM chat_history")
    await execute_query("DELETE FROM assets")
    await execute_query("DELETE FROM r2_emulated_files")
    await execute_query("DELETE FROM project_members")
    await execute_query("DELETE FROM projects")
    
    import shutil
    mock_r2_path = os.path.join("memory_store", "r2_mock")
    if os.path.exists(mock_r2_path):
        print("Cleaning up mock R2 store directory...")
        try:
            shutil.rmtree(mock_r2_path)
        except Exception:
            pass
    os.makedirs(mock_r2_path, exist_ok=True)

    # 1. Initialize schema
    print("Initializing database tables...")
    await init_db()
    
    # 2. Seed Users
    print("Seeding users table...")
    hashed_pwd = get_password_hash("admin123")
    created_at = datetime.now().isoformat(timespec="seconds")
    
    # Check if admin already exists
    existing_users = await execute_query("SELECT id FROM users WHERE username = ?", ["admin"])
    if not existing_users:
        await execute_query(
            "INSERT INTO users (username, hashed_password, email, created_at) VALUES (?, ?, ?, ?)",
            ["admin", hashed_pwd, "admin@lilia.studio", created_at]
        )
        print("✓ Created user 'admin' (password: admin123)")
    else:
        print("User 'admin' already exists.")

    # Get user id
    user_rows = await execute_query("SELECT id FROM users WHERE username = ?", ["admin"])
    user_id = user_rows[0]["id"]

    # 3. Seed Project
    proj_id = "demo_project"
    print(f"Seeding project '{proj_id}'...")
    
    existing_projects = await execute_query("SELECT id FROM projects WHERE id = ?", [proj_id])
    if not existing_projects:
        await execute_query(
            "INSERT INTO projects (id, display_name, source_lang, target_lang, content_type, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            [proj_id, "Demo Project", "ja", "vi", "novel", created_at]
        )
        print(f"✓ Created project '{proj_id}'")
    else:
        print(f"Project '{proj_id}' already exists.")

    # 4. Seed Project Membership
    existing_membership = await execute_query(
        "SELECT role FROM project_members WHERE user_id = ? AND project_id = ?",
        [user_id, proj_id]
    )
    if not existing_membership:
        await execute_query(
            "INSERT INTO project_members (user_id, project_id, role, joined_at) VALUES (?, ?, ?, ?)",
            [user_id, proj_id, "owner", created_at]
        )
        print(f"✓ Assigned 'owner' role to user 'admin' for project '{proj_id}'")
    else:
        print("Project membership already exists.")

    # 5. Seed R2 Storage (Glossary, Style, Entities)
    print("Seeding Cloudflare R2 / mock object storage...")
    
    # Glossary
    glossary_data = [
        {
            "source_term": "先輩",
            "target_term": "senpai",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "flexible",
            "context_variants": [
                {
                    "context": "hội thoại trang trọng hoặc lần đầu gặp",
                    "target_term": "tiền bối"
                },
                {
                    "context": "nhân vật thân thiết, tone thân mật",
                    "target_term": "anh/chị"
                }
            ],
            "context_note": "Giữ nguyên 'senpai' làm default cho flavor anime",
            "approved_at": "2026-06-06T10:00:00",
            "approved_by": "admin",
            "usage_count": 12
        },
        {
            "source_term": "海賊王",
            "target_term": "Vua Hải Tặc",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Danh hiệu chính thức, không được tự ý thay",
            "approved_at": "2026-06-06T10:00:00",
            "approved_by": "admin",
            "usage_count": 8
        }
    ]
    write_text(
        f"projects/{proj_id}/memory/glossary.yaml",
        yaml.dump(glossary_data, allow_unicode=True, sort_keys=False)
    )
    print("✓ Wrote glossary.yaml to R2")

    # Styles
    styles_data = {
        "project_id": proj_id,
        "source_lang": "ja",
        "target_lang": "vi",
        "content_type": "novel",
        "tone_note": "Văn phong văn học, lưu ý từ ngữ cổ trang trung cổ",
        "rules": [
            {
                "rule_id": "honorific-handling",
                "category": "honorific",
                "description": "Giữ nguyên các kính ngữ nếu mang tính đặc trưng văn hóa",
                "example_before": "Đàn anh Jo",
                "example_after": "Jo-senpai",
                "content_type": "novel",
                "source_lang": "ja",
                "target_lang": "vi",
                "approved_at": "2026-06-06T10:00:00",
                "approved_by": "admin"
            }
        ]
    }
    write_text(
        f"projects/{proj_id}/memory/styles.yaml",
        yaml.dump(styles_data, allow_unicode=True, sort_keys=False)
    )
    print("✓ Wrote styles.yaml to R2")

    # Entities
    entities_data = [
        {
            "entity_id": "jo",
            "canonical_name": "Jo",
            "source_name": "ジョー",
            "entity_type": "character",
            "source_lang": "ja",
            "target_lang": "vi",
            "pronouns": "cậu ấy/hắn",
            "aliases": ["John"],
            "notes": "Nhân vật chính, nam, 17 tuổi",
            "content_type": "novel",
            "approved_at": "2026-06-06T10:00:00",
            "approved_by": "admin",
            "mention_count": 25
        },
        {
            "entity_id": "richa",
            "canonical_name": "Richa",
            "source_name": "リチャ",
            "entity_type": "character",
            "source_lang": "ja",
            "target_lang": "vi",
            "pronouns": "cô ấy/nàng",
            "aliases": [],
            "notes": "Nữ phụ, pháp sư",
            "content_type": "novel",
            "approved_at": "2026-06-06T10:00:00",
            "approved_by": "admin",
            "mention_count": 14
        }
    ]
    write_text(
        f"projects/{proj_id}/memory/entities.yaml",
        yaml.dump(entities_data, allow_unicode=True, sort_keys=False)
    )
    print("✓ Wrote entities.yaml to R2")

    # Initialize empty corrections log
    write_text(f"projects/{proj_id}/memory/style_corrections.yaml", yaml.dump([], sort_keys=False))
    print("✓ Wrote empty style_corrections.yaml to R2")

    # Seed some chapters/docs
    doc_id = "doc_001"
    doc_meta = {
        "doc_id": doc_id,
        "title": "Chapter 1",
        "doc_type": "novel",
        "source_lang": "ja",
        "target_lang": "vi",
        "created_by": "admin",
        "created_at": created_at,
        "asset_count": 0,
        "status": "in_progress"
    }
    write_text(f"projects/{proj_id}/docs/{doc_id}/doc.yaml", yaml.dump(doc_meta, sort_keys=False))
    
    # Save original text asset
    source_text = '転移した際、ジョーは鮭のせいでリチャとはぐれてしまった。「戦うとなると面倒だな」とジョーは思いながら辺りを見回すと、扉が見えた。'
    write_text(f"projects/{proj_id}/docs/{doc_id}/assets/source.txt", source_text)
    
    print(f"✓ Initialized document '{doc_id}' for project '{proj_id}'")
    print("\nDatabase seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
