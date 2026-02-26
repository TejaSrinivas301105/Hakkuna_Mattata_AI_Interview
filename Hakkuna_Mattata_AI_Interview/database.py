import os
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorGridFSBucket
from dotenv import load_dotenv

load_dotenv()

MONGODB_URI = os.getenv("MONGODB_URI")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "hakkuna_mattata")


class Database:
    """MongoDB connection manager using motor (async driver)."""

    client: AsyncIOMotorClient = None
    db = None
    fs: AsyncIOMotorGridFSBucket = None

    @classmethod
    async def connect(cls):
        """Connect to MongoDB Atlas."""
        if not MONGODB_URI:
            raise ValueError("MONGODB_URI not found in .env file")

        cls.client = AsyncIOMotorClient(MONGODB_URI)
        cls.db = cls.client[MONGODB_DB_NAME]
        cls.fs = AsyncIOMotorGridFSBucket(cls.db, bucket_name="audio_files")

        # Verify connection
        await cls.client.admin.command("ping")
        print(f"✅ Connected to MongoDB: {MONGODB_DB_NAME}")

    @classmethod
    async def disconnect(cls):
        """Close MongoDB connection."""
        if cls.client:
            cls.client.close()
            print("🔌 MongoDB disconnected")

    # ─── Collection accessors ───────────────────────────────────────────

    @classmethod
    def candidates(cls):
        """Access the candidates collection."""
        return cls.db["candidates"]

    @classmethod
    def interviews(cls):
        """Access the screening interviews collection."""
        return cls.db["interviews"]

    @classmethod
    def deep_interviews(cls):
        """Access the deep technical interviews collection."""
        return cls.db["deep_interviews"]

    @classmethod
    def interview_reports(cls):
        """Access the interview reports collection."""
        return cls.db["interview_reports"]

    # ─── GridFS helpers ─────────────────────────────────────────────────

    @classmethod
    async def store_audio(cls, filename: str, file_data: bytes, metadata: dict = None) -> str:
        """Store an audio file in GridFS. Returns the file ID as string."""
        file_id = await cls.fs.upload_from_stream(
            filename,
            file_data,
            metadata=metadata or {},
        )
        return str(file_id)

    @classmethod
    async def get_audio(cls, file_id: str):
        """Retrieve an audio file from GridFS by ID."""
        from bson import ObjectId
        grid_out = await cls.fs.open_download_stream(ObjectId(file_id))
        contents = await grid_out.read()
        return contents, grid_out.filename
