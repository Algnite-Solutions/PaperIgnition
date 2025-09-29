import asyncio
import os
import sys
import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

# Add backend to Python path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from backend.app.db_utils import load_config
from backend.app.models.users import JobLog


class JobLogger:
    """Generic job logging utility for tracking job execution"""

    def __init__(self, config_path: str = None):
        if not config_path:
            config_path = os.path.join(os.path.dirname(__file__), "../backend/configs/test_config.yaml")

        self.config = load_config(config_path)
        self._engine = None
        self._session_factory = None
        self._setup_database()
        self._table_created = False

    def _setup_database(self):
        """Setup database connection"""
        db_config = self.config["USER_DB"]
        database_url = (
            f"postgresql+asyncpg://{db_config['db_user']}:{db_config['db_password']}"
            f"@{db_config['db_host']}:{db_config['db_port']}/{db_config['db_name']}"
        )

        self._engine = create_async_engine(
            database_url,
            echo=False,  # Set to True for SQL debugging
            future=True
        )

        self._session_factory = sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

    async def get_session(self) -> AsyncSession:
        """Get database session"""
        return self._session_factory()

    async def create_table_if_not_exists(self):
        """Create job_logs table if it doesn't exist"""
        if not self._table_created:
            try:
                async with self._engine.begin() as conn:
                    await conn.run_sync(JobLog.metadata.create_all)
                    print("✅ job_logs table created/verified")
                    self._table_created = True
            except Exception as e:
                print(f"❌ Error creating job_logs table: {e}")
                raise
    
    async def start_job_log(
        self,
        job_type: str,
        username: str = None,
        job_id: str = None
    ) -> str:
        """
        Start logging a job and return job_id

        Args:
            job_type: Type of job (e.g., "blog_generation", "paper_recommendation")
            username: Associated username if applicable
            job_id: Custom job ID (will generate one if not provided)

        Returns:
            str: The job_id for tracking this job
        """
        # Ensure table exists before first operation
        await self.create_table_if_not_exists()

        if not job_id:
            job_id = f"{job_type}_{uuid.uuid4().hex[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        async with self._session_factory() as session:
            try:
                job_log = JobLog(
                    job_type=job_type,
                    job_id=job_id,
                    status="running",
                    username=username,
                    start_time=datetime.now(timezone.utc)
                )

                session.add(job_log)
                await session.commit()
                print(f"✅ Started job log: {job_id}")
                return job_id

            except Exception as e:
                await session.rollback()
                print(f"❌ Error starting job log {job_id}: {e}")
                return job_id  # Return the ID anyway for continued operation

    async def update_job_log(
        self,
        job_id: str,
        status: str = None,
        error_message: str = None,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        Update an existing job log

        Args:
            job_id: Job identifier
            status: New status ("success", "failed", "partial", "running")
            error_message: Error message if failed
            details: Additional details as dictionary

        Returns:
            bool: True if updated successfully
        """
        async with self._session_factory() as session:
            try:
                # Find the job log
                result = await session.execute(
                    select(JobLog).where(JobLog.job_id == job_id)
                )
                job_log = result.scalar_one_or_none()

                if not job_log:
                    print(f"❌ Job log not found: {job_id}")
                    return False

                # Update fields
                if status is not None:
                    job_log.status = status
                if error_message is not None:
                    job_log.error_message = error_message
                if details is not None:
                    job_log.details = json.dumps(details)

                # Calculate duration if completing
                if status in ["success", "failed", "partial"] and job_log.start_time:
                    job_log.end_time = datetime.now(timezone.utc)
                    duration = job_log.end_time - job_log.start_time
                    job_log.duration_seconds = duration.total_seconds()

                job_log.updated_at = datetime.now(timezone.utc)

                await session.commit()
                print(f"✅ Updated job log: {job_id} -> {status}")
                return True

            except Exception as e:
                await session.rollback()
                print(f"❌ Error updating job log {job_id}: {e}")
                return False

    async def complete_job_log(
        self,
        job_id: str,
        error_message: str = None,
        details: Dict[str, Any] = None
    ) -> bool:
        """
        Complete a job log with final status

        Args:
            job_id: Job identifier
            status: Final status ("success", "failed", "partial")
            error_message: Error message if failed
            details: Additional details as dictionary

        Returns:
            bool: True if completed successfully
        """
        return await self.update_job_log(
            job_id=job_id,
            status="comnpleted",
            error_message=error_message,
            details=details
        )

    async def log_job_result(
        self,
        job_type: str,
        status: str,
        username: str = None,
        error_message: str = None,
        details: Dict[str, Any] = None,
        duration_seconds: float = None
    ) -> str:
        """
        Log a job result directly to database (one-shot logging)

        Args:
            job_type: Type of job (e.g., "blog_generation", "data_processing")
            status: Job status ("success", "failed", "partial")
            username: Associated username if applicable
            error_message: Error message if failed
            details: Additional details as dictionary
            duration_seconds: Job duration in seconds

        Returns:
            str: The generated job_id
        """
        job_id = f"{job_type}_{uuid.uuid4().hex[:8]}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        async with self._session_factory() as session:
            try:
                now = datetime.now(timezone.utc)
                start_time = now
                end_time = now

                # If duration is provided, calculate start_time
                if duration_seconds:
                    start_time = now - timedelta(seconds=duration_seconds)

                job_log = JobLog(
                    job_type=job_type,
                    job_id=job_id,
                    status=status,
                    username=username,
                    start_time=start_time,
                    end_time=end_time,
                    duration_seconds=duration_seconds,
                    error_message=error_message,
                    details=json.dumps(details) if details else None
                )

                session.add(job_log)
                await session.commit()
                print(f"✅ Job result logged: {job_id} -> {status}")
                return job_id

            except Exception as e:
                await session.rollback()
                print(f"❌ Error logging job result {job_id}: {e}")
                return job_id  # Return the ID anyway for tracking

    async def close(self):
        """Close database connections"""
        if self._engine:
            await self._engine.dispose()

    async def __aenter__(self):
        """Context manager entry - called when entering 'async with' block"""
        await self.create_table_if_not_exists()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - called when leaving 'async with' block"""
        await self.close()
        return False  # Don't suppress exceptions

# Example usage and testing
if __name__ == "__main__":
    async def test_context_manager():
        """Test using context manager (recommended approach)"""
        print("=== Testing Context Manager (Recommended) ===\n")

        # Test 1: Full job lifecycle with context manager
        print("1. Testing context manager pattern...")
        async with JobLogger() as logger:
            # Start a job
            job_id = await logger.start_job_log("data_processing", username="test@example.com")
            print(f"   Started job: {job_id}")

            # Update progress multiple times
            await logger.update_job_log(job_id, status="running", details={"progress": "25%"})
            print("   Updated: 25% complete")

            await logger.update_job_log(job_id, status="running", details={"progress": "75%"})
            print("   Updated: 75% complete")

            # Complete the job
            await logger.complete_job_log(
                job_id,
                details={"progress": "100%", "total_time": "120.5 seconds"}
            )
            print(f"   Completed job: {job_id}")
        # Database connection automatically closed here
        print("   Database connection automatically closed\n")

        # Test 2: One-shot logging with context manager
        print("2. Testing one-shot logging...")
        async with JobLogger() as logger:
            job_id = await logger.log_job_result(
                job_type="email_notification",
                status="success",
                username="admin@example.com",
                duration_seconds=45.2,
                details={"emails_sent": 150, "failures": 2}
            )
            print(f"   Logged completed job: {job_id}")
        print("   Database connection automatically closed\n")

        # Test 3: Error handling with context manager
        print("3. Testing error handling...")
        try:
            async with JobLogger() as logger:
                job_id = await logger.start_job_log("error_test")
                print(f"   Started job: {job_id}")

                # Simulate an error
                raise Exception("Simulated error during processing")

        except Exception as e:
            print(f"   Caught error: {e}")
            print("   Database connection still automatically closed\n")

    async def test_all():
        """Run all tests"""
        print("=== Job Logging Utility Tests ===\n")

        await test_context_manager()

        print("=== All tests completed ===")
        print("\n💡 Recommendation: Use the context manager pattern for better resource management!")

    asyncio.run(test_all())