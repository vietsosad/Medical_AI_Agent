"""
Chạy script này để dọn dẹp các bảng RAG legacy không còn sử dụng trên database local.
Giúp đồng bộ hoá môi trường database của bạn với cấu trúc Production hiện tại.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text

async def cleanup_local():
    load_dotenv()
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ DATABASE_URL is not set in .env")
        sys.exit(1)
        
    if db_url.startswith("postgresql://"):
        db_url = db_url.replace("postgresql://", "postgresql+asyncpg://")

    # Connect to DB
    engine = create_async_engine(db_url)
    try:
        async with engine.begin() as conn:
            print("🚀 Đang kiểm tra và dọn dẹp các bảng legacy trên Local DB...")
            
            tables_to_drop = [
                "triageknowledgebase",
                "triage_case_examples",
                "triage_protocol_documents"
            ]
            
            for table in tables_to_drop:
                try:
                    await conn.execute(text(f"DROP TABLE IF EXISTS {table} RESTRICT;"))
                    print(f"✅ Đã dọn dẹp bảng: {table}")
                except Exception as e:
                    print(f"⚠️ Không thể drop bảng {table}. Lỗi: {e}")
                    
            print("\nKiểm tra dữ liệu RAG mới (esi_knowledge_documents, mietic_cases)...")
            try:
                res_esi = await conn.execute(text("SELECT count(*) FROM esi_knowledge_documents;"))
                print(f"📄 esi_knowledge_documents: {res_esi.scalar()} dòng.")
                
                res_mietic = await conn.execute(text("SELECT count(*) FROM mietic_cases;"))
                print(f"🩺 mietic_cases: {res_mietic.scalar()} dòng.")
            except Exception as e:
                print(f"⚠️ Chưa có bảng RAG mới hoặc bị lỗi: {e}")
                print("💡 Bạn cần chạy: python scripts/knowledge/load_knowledge_stores.py")
                
            print("\n🎉 Dọn dẹp hoàn tất!")
    finally:
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(cleanup_local())
