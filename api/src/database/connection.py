# """Database connection and session management."""

# import os
# from sqlalchemy.ext.declarative import declarative_base
# from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
# from sqlalchemy.orm import sessionmaker

# DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@postgres:5432/hotel_booking")
# ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")

# engine = create_async_engine(ASYNC_DATABASE_URL)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, class_=AsyncSession)

# Base = declarative_base()

# async def get_database():
#     """Get database session."""
#     async with SessionLocal() as session:
#         try:
#             yield session
#         finally:
#             await session.close()

# async def init_db():
#     """Initialize database tables."""
#     async with engine.begin() as conn:
#         await conn.run_sync(Base.metadata.create_all)