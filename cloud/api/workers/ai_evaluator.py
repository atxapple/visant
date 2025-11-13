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

            # Get alert definition from cache
            from cloud.api.server import get_alert_definition_cache

            # Get definition from cache (device_definitions: {device_id: (definition_id, description_text)})
            definition_cache = get_alert_definition_cache()
            normal_description = ""
            alert_definition_id = None

            if capture.device_id in definition_cache:
                alert_definition_id, normal_description = definition_cache[capture.device_id]
                logger.debug(f"Using cached definition {alert_definition_id} for device {capture.device_id}")
            else:
                logger.warning(f"No alert definition found in cache for device {capture.device_id}")

            # Update classifier's normal_description before evaluation
            classifier = self.inference_service.classifier

            # Check if it's a ConsensusClassifier (has primary/secondary)
            if hasattr(classifier, "primary") and hasattr(classifier, "secondary"):
                # Update both primary and secondary classifiers
                if hasattr(classifier.primary, "normal_description"):
                    classifier.primary.normal_description = normal_description
                if hasattr(classifier.secondary, "normal_description"):
                    classifier.secondary.normal_description = normal_description
                logger.debug(f"Updated ConsensusClassifier descriptions for device {capture.device_id}")
            elif hasattr(classifier, "normal_description"):
                # Single classifier (OpenAI, Gemini, etc.)
                classifier.normal_description = normal_description
                logger.debug(f"Updated classifier description for device {capture.device_id}")

            # === SIMILARITY REUSE INTEGRATION ===
            # Check if we can reuse a cached classification to save AI cost
            similarity_hash = None
            reused_entry = None
            reuse_distance = None

            if self.inference_service.similarity_enabled:
                # Compute perceptual hash for similarity detection
                similarity_hash = self.inference_service._compute_similarity_hash(image_bytes)
                if similarity_hash is not None:
                    # Check cache for reusable classification
                    device_key = self.inference_service._device_key({"device_id": capture.device_id})
                    reused_entry, reuse_distance = self.inference_service._maybe_reuse_classification(
                        device_key, similarity_hash
                    )

            # Use cached result or run AI classifier
            if reused_entry is not None:
                # Cache hit - reuse previous classification (skip AI call)
                from cloud.api.similarity_cache import CachedEvaluation
                from cloud.ai.types import Classification

                classification = Classification(
                    state=reused_entry.state,
                    score=reused_entry.score,
                    reason=reused_entry.reason,
                )

                # Update metrics
                if hasattr(self.inference_service, 'similarity_cache_hits'):
                    self.inference_service.similarity_cache_hits += 1

                logger.info(
                    f"Reusing cached classification for {record_id}: "
                    f"state={classification.state}, score={classification.score:.2f}, "
                    f"hash_distance={reuse_distance}, threshold={self.inference_service.similarity_threshold}"
                )
            else:
                # Cache miss - run AI classification
                classification = self.inference_service.classifier.classify(image_bytes)

                # Update metrics
                if hasattr(self.inference_service, 'similarity_cache_misses'):
                    self.inference_service.similarity_cache_misses += 1

                logger.info(
                    f"AI evaluation for {record_id}: "
                    f"state={classification.state}, score={classification.score:.2f}"
                )

            # Update similarity cache with new result (if similarity enabled and cache available)
            if (
                self.inference_service.similarity_enabled
                and self.inference_service.similarity_cache is not None
                and similarity_hash is not None
                and reused_entry is None
            ):
                device_key = self.inference_service._device_key({"device_id": capture.device_id})
                self.inference_service.similarity_cache.update(
                    device_id=device_key,
                    record_id=record_id,
                    hash_hex=similarity_hash,
                    state=classification.state,
                    score=classification.score,
                    reason=classification.reason,
                    captured_at=capture.captured_at or datetime.now(timezone.utc)
                )

            # Update capture with results
            capture.state = classification.state
            capture.score = classification.score
            capture.reason = classification.reason
            capture.evaluation_status = "completed"
            capture.evaluated_at = datetime.now(timezone.utc)
            # Link to the alert definition that was used for this evaluation
            if alert_definition_id:
                capture.alert_definition_id = alert_definition_id

            db.commit()
            db.refresh(capture)

            logger.info(
                f"AI evaluation complete for {record_id}: state={classification.state}, "
                f"score={classification.score:.2f}"
            )

            # Broadcast capture event to web clients
            try:
                import asyncio
                from cloud.api.server import get_capture_hub

                capture_hub = get_capture_hub()

                # Prepare event data
                event = {
                    "event": "new_capture",
                    "capture_id": capture.record_id,
                    "device_id": capture.device_id,
                    "state": capture.state,
                    "score": capture.score,
                    "captured_at": capture.captured_at.isoformat() if capture.captured_at else None,
                    "evaluated_at": capture.evaluated_at.isoformat()
                }

                # Publish event (create event loop if needed for sync context)
                try:
                    loop = asyncio.get_event_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)

                loop.run_until_complete(
                    capture_hub.publish(capture.org_id, capture.device_id, event)
                )

                logger.debug(f"Published capture event for {record_id}")
            except Exception as publish_error:
                logger.warning(f"Failed to publish capture event for {record_id}: {publish_error}")
                # Don't fail the evaluation if event publishing fails

            # TODO: Trigger notifications if alert
            # if classification.state == "alert":
            #     notify_alert_detection(capture)

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
