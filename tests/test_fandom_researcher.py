import asyncio
from core.memory import ProjectMemory
from core.agents.fandom_researcher import FandomResearcher

async def main():
    # Setup test memory for a mock project
    proj_id = "test_fgo_project"
    mem = ProjectMemory(proj_id)
    
    # Clean previous test memory
    if mem.style.profile is None:
        mem.style.init_profile("en", "vi", "general", "Dịch chính xác")
    mem.glossary._entries = []
    mem.entities.registry = {}
    mem.style.profile.rules = []
    mem.glossary.save()
    mem.entities.save()
    mem.style.save()
    
    print("Testing FandomResearcher with Historical Figure: Richard I...")
    researcher = FandomResearcher(mem)
    
    try:
        res = await researcher.seed_project_memory(
            "Richard I of England",
            source_lang="en",
            target_lang="vi"
        )
        print("Seeding successful!")
        print(f"Glossary terms seeded: {res['glossary_count']}")
        print(f"Entities seeded: {res['entities_count']}")
        print(f"Style rules seeded: {res['style_count']}")
        
        # Verify the saved entries
        mem = ProjectMemory(proj_id) # Reload
        print("\n--- Seeded Glossary Sample ---")
        for entry in mem.glossary.get_all()[:3]:
            print(f"  {entry.source_term} -> {entry.target_term} ({entry.context_note})")
            
        print("\n--- Seeded Entities Sample ---")
        for ent in mem.entities.get_all()[:3]:
            print(f"  {ent.canonical_name} ({ent.source_name}) -> Notes/Pronouns: {ent.notes}")
            
    except Exception as e:
        print(f"FandomResearcher test failed: {e}")
    finally:
        await researcher.close()

if __name__ == "__main__":
    asyncio.run(main())
