import os
import sys
import asyncio
import base64
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

    print("Cleaning up old database records...")
    await execute_query("DELETE FROM segments")
    await execute_query("DELETE FROM chat_history")
    await execute_query("DELETE FROM assets")
    await execute_query("DELETE FROM r2_emulated_files")
    await execute_query("DELETE FROM project_members")
    await execute_query("DELETE FROM projects")
    await execute_query("DELETE FROM users")
    
    import shutil
    mock_r2_path = os.path.join("memory_store", "r2_mock")
    if os.path.exists(mock_r2_path):
        print("Cleaning up mock R2 store directory...")
        try:
            shutil.rmtree(mock_r2_path)
        except Exception:
            pass
    os.makedirs(mock_r2_path, exist_ok=True)

    print("Initializing database tables...")
    await init_db()
    
    created_at = datetime.now().isoformat(timespec="seconds")
    
    # Seed Users
    print("Seeding users...")
    admin_hash = get_password_hash("admin123")
    mock_hash = get_password_hash("mock123")
    
    await execute_query(
        "INSERT INTO users (username, hashed_password, email, created_at) VALUES (?, ?, ?, ?)",
        ["admin", admin_hash, "admin@lilia.studio", created_at]
    )
    await execute_query(
        "INSERT INTO users (username, hashed_password, email, created_at) VALUES (?, ?, ?, ?)",
        ["mock_google_user", mock_hash, "mock.google.user@gmail.com", created_at]
    )
    print("  OK - Created users: 'admin' (admin123), 'mock_google_user' (mock123)")

    # Get user IDs
    rows = await execute_query("SELECT id, username FROM users")
    user_map = {r["username"]: r["id"] for r in rows}
    admin_id = user_map["admin"]
    mock_id = user_map["mock_google_user"]

    # Seed Project
    proj_id = "richard_project"
    print(f"Seeding project '{proj_id}'...")
    await execute_query(
        "INSERT INTO projects (id, display_name, description, source_lang, target_lang, content_type, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [proj_id, "Nghiên Cứu Richard Sư Tử Tâm", "Tuyển tập tư liệu đa ngôn ngữ về Vua Richard I: thơ Pháp cổ Ja nus hom pris, tiểu sử tiếng Nhật, bản đồ pháo đài Chateau Gaillard.", "multi", "vi", "novel", created_at]
    )
    
    # Assign owners
    await execute_query(
        "INSERT INTO project_members (user_id, project_id, role, joined_at) VALUES (?, ?, ?, ?)",
        [admin_id, proj_id, "owner", created_at]
    )
    await execute_query(
        "INSERT INTO project_members (user_id, project_id, role, joined_at) VALUES (?, ?, ?, ?)",
        [mock_id, proj_id, "owner", created_at]
    )
    print("  OK - Configured project memberships.")

    # Seed R2 Storage (Glossary, Style, Entities)
    print("Seeding Cloudflare R2 files...")
    
    # Glossary (12 entries)
    glossary_data = [
        {
            "source_term": "獅子心王",
            "target_term": "Richard Sư Tử Tâm",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Biệt hiệu chính thức của Richard I",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 42
        },
        {
            "source_term": "十字軍",
            "target_term": "Thập Tự Chinh",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Cuộc viễn chinh quân sự tôn giáo",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 55
        },
        {
            "source_term": "エルサレム",
            "target_term": "Jerusalem",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Thánh địa lịch sử",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 29
        },
        {
            "source_term": "Ja nus hom pris",
            "target_term": "Không kẻ tù đày nào",
            "source_lang": "fr",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Tên bài thơ viết trong ngục của Richard I",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 12
        },
        {
            "source_term": "Château Gaillard",
            "target_term": "Pháo đài Gaillard",
            "source_lang": "fr",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Pháo đài đá do Richard I xây dựng bên sông Seine",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 18
        },
        {
            "source_term": "サラディン",
            "target_term": "Saladin",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Thủ lĩnh quân Hồi giáo Ayyub",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 51
        },
        {
            "source_term": "王都",
            "target_term": "Vương Đô",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Thủ đô hoàng gia",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 22
        },
        {
            "source_term": "捕虜",
            "target_term": "tù binh",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "flexible",
            "context_variants": [],
            "context_note": "Người bị bắt giữ",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 14
        },
        {
            "source_term": "身代金",
            "target_term": "tiền chuộc",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Khoản tiền giải phóng hoàng gia",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 9
        },
        {
            "source_term": "同盟",
            "target_term": "đồng minh",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "flexible",
            "context_variants": [],
            "context_note": "Hợp tác giữa các vương quốc",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 16
        },
        {
            "source_term": "アッコン",
            "target_term": "Acre",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Thành phố cảng Akko/Acre",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 31
        },
        {
            "source_term": "休戦",
            "target_term": "đình chiến",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "strictness": "fixed",
            "context_variants": [],
            "context_note": "Ngưng bắn tạm thời",
            "approved_at": created_at,
            "approved_by": "admin",
            "usage_count": 8
        }
    ]
    ja_vi_glossary = [e for e in glossary_data if e["source_lang"] == "ja" and e["target_lang"] == "vi"]
    fr_vi_glossary = [e for e in glossary_data if e["source_lang"] == "fr" and e["target_lang"] == "vi"]
    write_text(
        f"projects/{proj_id}/memory/ja_vi_glossary.yaml",
        yaml.dump(ja_vi_glossary, allow_unicode=True, sort_keys=False)
    )
    write_text(
        f"projects/{proj_id}/memory/fr_vi_glossary.yaml",
        yaml.dump(fr_vi_glossary, allow_unicode=True, sort_keys=False)
    )

    # Styles (6 entries)
    styles_data = {
        "project_id": proj_id,
        "source_lang": "ja",
        "target_lang": "vi",
        "content_type": "novel",
        "tone_note": "Văn phong sử thi trung cổ, ngôn từ trang nghiêm trang trọng",
        "rules": [
            {
                "rule_id": "monarch-address",
                "category": "honorific",
                "description": "Sử dụng đại từ trang trọng (Đức vua, Bệ hạ) khi dịch các ngôi vương",
                "example_before": "Richard nói",
                "example_after": "Đức vua Richard phán",
                "content_type": "novel",
                "source_lang": "ja",
                "target_lang": "vi",
                "approved_at": created_at,
                "approved_by": "admin"
            },
            {
                "rule_id": "poetic-translation",
                "category": "style",
                "description": "Dịch thơ ca trung cổ cần giữ nhịp điệu uyển chuyển và ngôn từ hoài cổ tinh tế",
                "example_before": "Tôi viết bài thơ trong ngục",
                "example_after": "Lời thơ y cất lên chốn ngục tù",
                "content_type": "novel",
                "source_lang": "fr",
                "target_lang": "vi",
                "approved_at": created_at,
                "approved_by": "admin"
            },
            {
                "rule_id": "annotation-needed",
                "category": "vocabulary",
                "description": "Thêm chú thích hoặc điển tích lịch sử đối với các địa danh và bài thơ tự sự",
                "example_before": "Jerusalem",
                "example_after": "Jerusalem [Thánh địa xảy ra xung đột Thập Tự Chinh]",
                "content_type": "novel",
                "source_lang": "ja",
                "target_lang": "vi",
                "approved_at": created_at,
                "approved_by": "admin"
            },
            {
                "rule_id": "place-name-transliteration",
                "category": "translation",
                "description": "Việt hóa danh từ riêng lịch sử thay vì giữ nguyên phiên âm",
                "example_before": "Akkon",
                "example_after": "Thành Acre",
                "content_type": "novel",
                "source_lang": "ja",
                "target_lang": "vi",
                "approved_at": created_at,
                "approved_by": "admin"
            },
            {
                "rule_id": "military-rank",
                "category": "vocabulary",
                "description": "Chuẩn hóa xưng hô cấp bậc quân đội trung cổ (hiệp sĩ, kỵ sĩ, thống lĩnh)",
                "example_before": "tướng quân",
                "example_after": "thống lĩnh",
                "content_type": "novel",
                "source_lang": "ja",
                "target_lang": "vi",
                "approved_at": created_at,
                "approved_by": "admin"
            },
            {
                "rule_id": "crusade-terminology",
                "category": "term",
                "description": "Chuẩn hóa thuật ngữ viễn chinh tôn giáo và quân sự lịch sử",
                "example_before": "quân đội chữ thập",
                "example_after": "quân Thập Tự Chinh",
                "content_type": "novel",
                "source_lang": "ja",
                "target_lang": "vi",
                "approved_at": created_at,
                "approved_by": "admin"
            }
        ]
    }
    ja_vi_rules = [r for r in styles_data["rules"] if r.get("source_lang") == "ja" and r.get("target_lang") == "vi"]
    fr_vi_rules = [r for r in styles_data["rules"] if r.get("source_lang") == "fr" and r.get("target_lang") == "vi"]
    
    write_text(
        f"projects/{proj_id}/memory/ja_vi_styles.yaml",
        yaml.dump({
            "project_id": proj_id,
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "tone_note": "Văn phong sử thi trung cổ, ngôn từ trang nghiêm trang trọng",
            "rules": ja_vi_rules
        }, allow_unicode=True, sort_keys=False)
    )
    write_text(
        f"projects/{proj_id}/memory/fr_vi_styles.yaml",
        yaml.dump({
            "project_id": proj_id,
            "source_lang": "fr",
            "target_lang": "vi",
            "content_type": "novel",
            "tone_note": "Giữ nhịp điệu thơ cổ kính",
            "rules": fr_vi_rules
        }, allow_unicode=True, sort_keys=False)
    )

    # Entities (8 entries)
    entities_data = [
        {
            "entity_id": "richard",
            "canonical_name": "Richard I",
            "source_name": "リチャード1世",
            "entity_type": "character",
            "source_lang": "ja",
            "target_lang": "vi",
            "pronouns": "Đức vua / Ngài",
            "aliases": ["Richard", "Lionheart", "Richard Coeur de Lion"],
            "notes": "Vua nước Anh, dũng cảm và kiêu hùng, biệt danh Richard Sư Tử Tâm, tác giả bài thơ Ja nus hom pris.",
            "content_type": "novel",
            "approved_at": created_at,
            "approved_by": "admin",
            "mention_count": 124
        },
        {
            "entity_id": "saladin",
            "canonical_name": "Saladin",
            "source_name": "サラディン",
            "entity_type": "character",
            "source_lang": "ja",
            "target_lang": "vi",
            "pronouns": "Sultan / Ngài",
            "aliases": [],
            "notes": "Vị Sultan lỗi lạc của vương triều Ayyub, đối thủ đáng trọng của Richard.",
            "content_type": "novel",
            "approved_at": created_at,
            "approved_by": "admin",
            "mention_count": 98
        },
        {
            "entity_id": "duernstein",
            "canonical_name": "Dürnstein",
            "source_name": "Dürnstein",
            "entity_type": "location",
            "source_lang": "fr",
            "target_lang": "vi",
            "pronouns": "nơi đây",
            "aliases": [],
            "notes": "Lâu đài tại Áo nơi Richard I bị giam giữ bởi Leopold V từ năm 1192 đến 1194.",
            "content_type": "novel",
            "approved_at": created_at,
            "approved_by": "admin",
            "mention_count": 15
        },
        {
            "entity_id": "philip",
            "canonical_name": "Philip II",
            "source_name": "フィリップ2世",
            "entity_type": "character",
            "source_lang": "ja",
            "target_lang": "vi",
            "pronouns": "Đức vua",
            "aliases": [],
            "notes": "Vua nước Pháp, đồng minh nhưng đầy mưu mô của Richard.",
            "content_type": "novel",
            "approved_at": created_at,
            "approved_by": "admin",
            "mention_count": 42
        },
        {
            "entity_id": "leopold",
            "canonical_name": "Leopold V",
            "source_name": "Leopold V",
            "entity_type": "character",
            "source_lang": "de",
            "target_lang": "vi",
            "pronouns": "Công tước / Ngài",
            "aliases": [],
            "notes": "Công tước nước Áo, người bắt giữ Vua Richard trên đường trở về từ Thập Tự Chinh.",
            "content_type": "novel",
            "approved_at": created_at,
            "approved_by": "admin",
            "mention_count": 28
        },
        {
            "entity_id": "blondel",
            "canonical_name": "Blondel",
            "source_name": "Blondel",
            "entity_type": "character",
            "source_lang": "fr",
            "target_lang": "vi",
            "pronouns": "anh ấy / người nghệ sĩ",
            "aliases": ["Blondel de Nesle"],
            "notes": "Nghệ sĩ hát rong trung thành, người đi khắp các lâu đài tìm kiếm Vua Richard.",
            "content_type": "novel",
            "approved_at": created_at,
            "approved_by": "admin",
            "mention_count": 19
        },
        {
            "entity_id": "acre",
            "canonical_name": "Thành Acre",
            "source_name": "アッコン",
            "entity_type": "location",
            "source_lang": "ja",
            "target_lang": "vi",
            "pronouns": "thành lũy",
            "aliases": ["Acre", "Akko"],
            "notes": "Thành phố cảng chiến lược bị bao vây trong cuộc Thập Tự Chinh thứ ba.",
            "content_type": "novel",
            "approved_at": created_at,
            "approved_by": "admin",
            "mention_count": 35
        },
        {
            "entity_id": "chateau_gaillard",
            "canonical_name": "Château Gaillard",
            "source_name": "Château Gaillard",
            "entity_type": "location",
            "source_lang": "fr",
            "target_lang": "vi",
            "pronouns": "tòa thành",
            "aliases": [],
            "notes": "Tòa lâu đài pháo đài đá do Vua Richard xây dựng tại Normandy để bảo vệ đất đai.",
            "content_type": "novel",
            "approved_at": created_at,
            "approved_by": "admin",
            "mention_count": 32
        }
    ]
    ja_vi_entities = [e for e in entities_data if e["source_lang"] == "ja" and e["target_lang"] == "vi"]
    fr_vi_entities = [e for e in entities_data if e["source_lang"] == "fr" and e["target_lang"] == "vi"]
    de_vi_entities = [e for e in entities_data if e["source_lang"] == "de" and e["target_lang"] == "vi"]
    
    write_text(
        f"projects/{proj_id}/memory/ja_vi_entities.yaml",
        yaml.dump(ja_vi_entities, allow_unicode=True, sort_keys=False)
    )
    write_text(
        f"projects/{proj_id}/memory/fr_vi_entities.yaml",
        yaml.dump(fr_vi_entities, allow_unicode=True, sort_keys=False)
    )
    write_text(
        f"projects/{proj_id}/memory/de_vi_entities.yaml",
        yaml.dump(de_vi_entities, allow_unicode=True, sort_keys=False)
    )

    # Empty corrections logs
    write_text(f"projects/{proj_id}/memory/ja_vi_style_corrections.yaml", yaml.dump([], sort_keys=False))
    write_text(f"projects/{proj_id}/memory/fr_vi_style_corrections.yaml", yaml.dump([], sort_keys=False))
    print("  OK - Seeded glossary, styles, and entities to R2.")

    # Seed Documents
    # Document 1: Chapter 01 (Poem - Pre-translated)
    doc_1 = "doc_001"
    doc_meta_1 = {
        "doc_id": doc_1,
        "title": "Thơ Cổ - Ja nus hom pris (Khúc 1)",
        "doc_type": "novel",
        "source_lang": "fr",
        "target_lang": "vi",
        "created_by": "admin",
        "created_at": created_at,
        "asset_count": 0,
        "status": "completed"
    }
    write_text(f"projects/{proj_id}/docs/{doc_1}/doc.yaml", yaml.dump(doc_meta_1, sort_keys=False))
    write_text(
        f"projects/{proj_id}/docs/{doc_1}/assets/source.txt",
        "Ja nus hom pris ne dira sa raison\nAdroitement, s'ansi com dolans non;\nMais por confort puet il faire chanson.\nProier y puet, mais las ne porra mie.\nMolt ai d'amis, mais povre est la clergie;\nHonte i avront, se por ma reancon"
    )
    
    # Seed D1 segments for Document 1 (6 segments)
    segments_to_seed = [
        {
            "segment_id": "seg_1",
            "source_text": "Ja nus hom pris ne dira sa raison",
            "target_text": "Kẻ bị giam cầm chẳng thể cất lời bày tỏ"
        },
        {
            "segment_id": "seg_2",
            "source_text": "Adroitement, s'ansi com dolans non;",
            "target_text": "Được trọn lòng, ngoại trừ những tiếng than u uất;"
        },
        {
            "segment_id": "seg_3",
            "source_text": "Mais por confort puet il faire chanson.",
            "target_text": "Nhưng để ủi an, y có thể cất cao tiếng hát."
        },
        {
            "segment_id": "seg_4",
            "source_text": "Proier y puet, mais las ne porra mie.",
            "target_text": "Lời thỉnh cầu y dâng lên, nhưng mỏi mòn chẳng thể thấu."
        },
        {
            "segment_id": "seg_5",
            "source_text": "Molt ai d'amis, mais povre est la clergie;",
            "target_text": "Bao bằng hữu y trao niềm tin, nay chỉ còn sự nghèo nàn giả dối."
        },
        {
            "segment_id": "seg_6",
            "source_text": "Honte i avront, se por ma reancon",
            "target_text": "Họ sẽ phải chuốc lấy nỗi hổ thẹn này, nếu để y chịu kiếp giam cầm."
        }
    ]
    
    for seg in segments_to_seed:
        await execute_query(
            "INSERT INTO segments (project_id, doc_id, segment_id, segment_type, source_text, target_text, approved_by, approved_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [proj_id, doc_1, seg["segment_id"], "paragraph", seg["source_text"], seg["target_text"], admin_id, created_at]
        )
    print("  OK - Seeded Chapter 1 document and segments.")

    # Document 2: Chapter 02 (Wikipedia JP - Untranslated)
    doc_2 = "doc_002"
    doc_meta_2 = {
        "doc_id": doc_2,
        "title": "Tiểu Sử - Richard I (Wikipedia JP)",
        "doc_type": "novel",
        "source_lang": "ja",
        "target_lang": "vi",
        "created_by": "admin",
        "created_at": created_at,
        "asset_count": 0,
        "status": "in_progress"
    }
    write_text(f"projects/{proj_id}/docs/{doc_2}/doc.yaml", yaml.dump(doc_meta_2, sort_keys=False))
    write_text(
        f"projects/{proj_id}/docs/{doc_2}/assets/source.txt",
        "リチャード1世は中世イングランド of 国王であり、その勇猛さから「獅子心王」と称された。第3回十字軍において đại hoạt dược し、イスラム of 英雄サラディンと激戦を繰り広げたことで有名である。"
    )
    print("  OK - Seeded Chapter 2 document (untranslated).")

    # Document 3: Chapter 03 (Manga)
    doc_3 = "doc_003"
    doc_meta_3 = {
        "doc_id": doc_3,
        "title": "Bản Vẽ - Pháo Đài Chateau Gaillard",
        "doc_type": "manga",
        "source_lang": "fr",
        "target_lang": "vi",
        "created_by": "admin",
        "created_at": created_at,
        "asset_count": 0,
        "status": "in_progress"
    }
    write_text(f"projects/{proj_id}/docs/{doc_3}/doc.yaml", yaml.dump(doc_meta_3, sort_keys=False))
    print("  OK - Seeded Chapter 3 document (manga type).")

    # Document 4: Chapter 04 (French - Untranslated)
    doc_4 = "doc_004"
    doc_meta_4 = {
        "doc_id": doc_4,
        "title": "Ký Sự - Truyền Thuyết Blondel (French)",
        "doc_type": "novel",
        "source_lang": "fr",
        "target_lang": "vi",
        "created_by": "admin",
        "created_at": created_at,
        "asset_count": 0,
        "status": "in_progress"
    }
    write_text(f"projects/{proj_id}/docs/{doc_4}/doc.yaml", yaml.dump(doc_meta_4, sort_keys=False))
    write_text(
        f"projects/{proj_id}/docs/{doc_4}/assets/source.txt",
        "Le troubadour Blondel chanta devant chaque château pour retrouver le roi Richard."
    )
    print("  OK - Seeded Chapter 4 document (untranslated).")

    # Document 5: Chapter 05 (English - Untranslated)
    doc_5 = "doc_005"
    doc_meta_5 = {
        "doc_id": doc_5,
        "title": "Hồ Sơ - Khoản Tiền Chuộc Hoàng Gia (English)",
        "doc_type": "novel",
        "source_lang": "en",
        "target_lang": "vi",
        "created_by": "admin",
        "created_at": created_at,
        "asset_count": 0,
        "status": "in_progress"
    }
    write_text(f"projects/{proj_id}/docs/{doc_5}/doc.yaml", yaml.dump(doc_meta_5, sort_keys=False))
    write_text(
        f"projects/{proj_id}/docs/{doc_5}/assets/source.txt",
        "The Holy Roman Emperor Henry VI demanded 150,000 marks for the release of Richard."
    )
    print("  OK - Seeded Chapter 5 document (untranslated).")

    # Document 6: Chapter 06 (Japanese - Untranslated)
    doc_6 = "doc_006"
    doc_meta_6 = {
        "doc_id": doc_6,
        "title": "Nhật Ký - Trận Chiến Tại Acre (JP)",
        "doc_type": "novel",
        "source_lang": "ja",
        "target_lang": "vi",
        "created_by": "admin",
        "created_at": created_at,
        "asset_count": 0,
        "status": "in_progress"
    }
    write_text(f"projects/{proj_id}/docs/{doc_6}/doc.yaml", yaml.dump(doc_meta_6, sort_keys=False))
    write_text(
        f"projects/{proj_id}/docs/{doc_6}/assets/source.txt",
        "アッコン包囲戦において、リチャード1世は自ら病を押して前線で指揮を執った。"
    )
    print("  OK - Seeded Chapter 6 document (untranslated).")

    # Seed Chat History
    print("Seeding Chat History...")
    chats_to_seed = [
        {
            "id": "chat_1",
            "sender": "user",
            "text": "Dịch bài thơ Ja nus hom pris của Vua Richard xem sao, nhớ thêm chú thích hoàn cảnh sáng tác nhé.",
            "status": "done",
            "is_general_chat": 1
        },
        {
            "id": "chat_2",
            "sender": "assistant",
            "text": "Tôi đã nhận diện bài thơ bằng tiếng Pháp cổ (Old French) của Richard I viết trong ngục tối lâu đài Dürnstein năm 1192. Đang tiến hành dịch thơ song thất lục bát kèm chú thích điển tích.",
            "status": "done",
            "is_general_chat": 1
        },
        {
            "id": "chat_3",
            "sender": "assistant",
            "text": "Đã hoàn thành dịch 3 câu thơ đầu. Kết quả dịch kèm chú thích lịch sử đã được lưu trữ.",
            "status": "done",
            "is_general_chat": 1
        },
        {
            "id": "chat_4",
            "sender": "user",
            "text": "Tuyệt vời, bản dịch giữ được chất u sầu của người bị giam cầm.",
            "status": "done",
            "is_general_chat": 1
        }
    ]
    for chat in chats_to_seed:
        await execute_query(
            "INSERT INTO chat_history (id, project_id, doc_id, sender, text, status, is_image_workflow, is_general_chat, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [chat["id"], proj_id, doc_1, chat["sender"], chat["text"], chat["status"], 0, chat["is_general_chat"], created_at]
        )
    print("  OK - Seeded chat history messages.")

    print("\nDatabase seeding completed successfully.")

if __name__ == "__main__":
    asyncio.run(seed())
