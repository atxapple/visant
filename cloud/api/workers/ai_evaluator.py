"""Background AI evaluation worker for uploaded captures."""

import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.orm import Session

from cloud.api.database import Capture
from cloud.api.service import InferenceService
from cloud.api.storage.presigned import generate_presigned_url

logger = logging.getLogger(__name__)


class CloudAIEvaluator:
    """
    Background worker for AI evaluation of uploaded captures.

    Reuses the existing InferenceService from the old API.
    """

    def __init__(self, inference_service: InferenceService):
        """
        Initialize the evaluator.

        Args:
            inference_service: The InferenceService instance for running AI classification
        """
        self.inference_service = inference_service

    def evaluate_capture(
        self,
        record_id: str,
        image_bytes: bytes,
        db: Session
    ) -> Optional[dict]:
        """
        Evaluate a capture with Cloud AI.

        Args:
            record_id: The capture record_id to evaluate
            image_bytes: The raw image bytes
            db: Database session

        Returns:
            Dictionary with evaluation results or None if failed
        """
        try:
            # Get capture from database
            capture = db.query(Capture).filter(Capture.record_id == record_id).first()
            if not capture:
                logger.error(f"Capture not found: {record_id}")
                return None

            # Update status to processing
            capture.evaluation_status = "processing"
            db.commit()

            logger.info(f"Starting AI evaluation for capture: {record_id}")

            # Run classification using existing InferenceService
            # The classifier.classify() method expects bytes and returns Classification object
            classification = self.inference_service.classifier.classify(image_bytes)

            # Update capture with results
            capture.state = classification.state
            capture.score = classification.score
            capture.reason = classification.reason
            capture.evaluation_status = "completed"
            capture.evaluated_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(capture)

            logger.info(
                f"AI evaluation complete for {record_id}: state={classification.state}, "
                f"score={classification.score:.2f}"
            )

            # TODO: Trigger notifications if abnormal
            # if classification.state == "abnormal":
            #     notify_abnormal_detection(capture)

            return {
                "record_id": record_id,
                "state": classification.state,
                "score": classification.score,
                "reason": classification.reason,
                "evaluated_at": capture.evaluated_at.isoformat()
            }

        except Exception as e:
            logger.exception(f"AI evaluation failed for {record_id}: {e}")

            # Mark as failed in database
            try:
                capture = db.query(Capture).filter(Capture.record_id == record_id).first()
                if capture:
                    capture.evaluation_status = "failed"
                    capture.reason = f"Evaluation error: {str(e)}"
                    db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update error status: {db_error}")

            return None


def evaluate_capture_async(
    record_id: str,
    image_bytes: bytes,
    inference_service: InferenceService
):
    """
    Async wrapper for background task execution.

    This function is called by FastAPI BackgroundTasks.
    Creates its own database session (background tasks must not reuse request sessions).

    Args:
        record_id: The capture record_id
        image_bytes: The image data
        inference_service: InferenceService instance
    """
    from cloud.api.database import SessionLocal

    # Create new database session for background task
    db = SessionLocal()
    try:
        evaluator = CloudAIEvaluator(inference_service)
        result = evaluator.evaluate_capture(record_id, image_bytes, db)

        if result:
            logger.info(f"Background evaluation succeeded: {record_id}")
        else:
            logger.error(f"Background evaluation failed: {record_id}")
    finally:
        db.close()  # Always close the session
