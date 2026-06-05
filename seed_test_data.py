import os
import json
import base64
import hashlib
from pathlib import Path
import yaml

def get_password_hash(password: str) -> str:
    salt = os.urandom(16)
    iterations = 100000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{iterations}${base64.b64encode(salt).decode()}${base64.b64encode(dk).decode()}"

def seed():
    # 1. Create users
    users_dir = Path("memory_store")
    users_dir.mkdir(parents=True, exist_ok=True)
    users_file = users_dir / "users.json"
    
    hashed_pwd = get_password_hash("admin123")
    users_data = {
        "admin": {
            "password": hashed_pwd,
            "email": "admin@lilia.studio"
        }
    }
    users_file.write_text(json.dumps(users_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Seeded memory_store/users.json with user 'admin' (password: admin123)")

    # 2. Create demo_project data
    proj_id = "demo_project"
    proj_dir = Path("projects") / proj_id
    proj_dir.mkdir(parents=True, exist_ok=True)
    
    # project.yaml
    proj_yaml = {
        "project_id": proj_id,
        "source_lang": "ja",
        "target_lang": "vi",
        "content_type": "novel",
        "tone_note": "Dịch mượt mà, dùng đại từ nhân xưng phù hợp bối cảnh"
    }
    (proj_dir / "project.yaml").write_text(yaml.dump(proj_yaml, allow_unicode=True, sort_keys=False), encoding="utf-8")
    
    # memory dirs
    mem_dir = proj_dir / "memory"
    for subdir in ["glossaries", "styles", "entities"]:
        (mem_dir / subdir).mkdir(parents=True, exist_ok=True)
        
    # glossary.yaml
    glossary_data = [
        {
            "source_term": "先輩",
            "target_term": "Tiền bối",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "context_note": "Giữ nguyên kính ngữ",
            "approved_at": "2026-06-05T00:00:00",
            "approved_by": "human",
            "usage_count": 12
        },
        {
            "source_term": "陛下",
            "target_term": "Bệ hạ",
            "source_lang": "ja",
            "target_lang": "vi",
            "content_type": "novel",
            "context_note": "Danh xưng trang trọng cho hoàng đế",
            "approved_at": "2026-06-05T00:00:00",
            "approved_by": "human",
            "usage_count": 8
        }
    ]
    (mem_dir / "glossaries" / f"{proj_id}.yaml").write_text(yaml.dump(glossary_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    
    # styles.yaml
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
                "approved_at": "2026-06-05T00:00:00",
                "approved_by": "human"
            }
        ]
    }
    (mem_dir / "styles" / f"{proj_id}.yaml").write_text(yaml.dump(styles_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    
    # entities.yaml
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
            "approved_at": "2026-06-05T00:00:00",
            "approved_by": "human",
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
            "approved_at": "2026-06-05T00:00:00",
            "approved_by": "human",
            "mention_count": 14
        }
    ]
    (mem_dir / "entities" / f"{proj_id}.yaml").write_text(yaml.dump(entities_data, allow_unicode=True, sort_keys=False), encoding="utf-8")
    
    # Chapters
    ch_dir = proj_dir / "chapters"
    ch_dir.mkdir(parents=True, exist_ok=True)
    
    # Chapter 1
    (ch_dir / "ch001").mkdir(parents=True, exist_ok=True)
    draft_1 = 'Khi dịch chuyển, Jo bị lạc khỏi Richa vì con cá hồi. "Nếu phải đánh nhau thì phiền đấy" - Jo vừa nghĩ vừa nhìn quanh thì thấy một cánh cửa. Dù rõ ràng là cái bẫy, nhưng có lẽ đó là lối thoát, nên Jo bước vào và thấy Richa đang đứng giữa không gian trắng. "Mày cũng đến à," Richa nói. Jo im lặng không đáp. "Tao sẽ bảo vệ mày, đừng lo.'
    (ch_dir / "ch001" / "draft.md").write_text(draft_1, encoding="utf-8")
    (ch_dir / "ch001" / "approved.md").write_text(draft_1.replace("cá hồi", "masu"), encoding="utf-8")
    
    # Chapter 2
    (ch_dir / "ch002").mkdir(parents=True, exist_ok=True)
    draft_2 = 'Trong căn phòng trống rỗng, Jo và Richa nhìn thấy một quả cầu ma thuật màu xanh lục đang trôi nổi lơ lửng. "Đừng chạm vào nó," Richa cảnh báo, nhưng Jo đã lỡ tiến sát lại gần. Một luồng sáng chói mắt bùng lên.'
    (ch_dir / "ch002" / "draft.md").write_text(draft_2, encoding="utf-8")
    (ch_dir / "ch002" / "approved.md").write_text(draft_2, encoding="utf-8")

    # Chapter 3
    (ch_dir / "ch003").mkdir(parents=True, exist_ok=True)
    draft_3 = 'Sau khi luồng sáng tắt, cả hai phát hiện mình đang đứng giữa một khu rừng rậm rạp. Tiếng gió rít qua tán lá vang lên như những tiếng thì thầm ma quái.'
    (ch_dir / "ch003" / "draft.md").write_text(draft_3, encoding="utf-8")
    (ch_dir / "ch003" / "approved.md").write_text(draft_3, encoding="utf-8")

    print(f"✓ Seeded project '{proj_id}' with metadata, glossary, styles, entities and chapters.")

if __name__ == "__main__":
    seed()
