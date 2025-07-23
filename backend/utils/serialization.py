import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

T = TypeVar("T")

logger = logging.getLogger(__name__)


class JSONSerializationError(Exception):
    """Raised when JSON serialization/deserialization fails."""

    pass


class JSONField:
    @staticmethod
    def serialize(data: Any) -> Optional[str]:
        if data is None:
            return None

        if isinstance(data, (list, dict, tuple)) and len(data) == 0:
            return None

        try:
            return json.dumps(data, default=_json_serializer, ensure_ascii=False)
        except (TypeError, ValueError) as e:
            error_msg = f"Failed to serialize data to JSON: {str(e)}"
            logger.error(
                error_msg, extra={"data_type": type(data).__name__, "error": str(e)}
            )
            raise JSONSerializationError(error_msg) from e

    @staticmethod
    def deserialize(
        data: Optional[str], default_type: Type[T] = list
    ) -> Union[T, List, Dict]:
        if not data or data.strip() == "":
            return default_type() if callable(default_type) else default_type

        try:
            result = json.loads(data)
            logger.debug(
                f"Successfully deserialized JSON data",
                extra={"result_type": type(result).__name__},
            )
            return result
        except (json.JSONDecodeError, TypeError) as e:
            error_msg = f"Failed to deserialize JSON data: {str(e)}"
            logger.error(
                error_msg,
                extra={
                    "data_preview": data[:100] if len(data) > 100 else data,
                    "error": str(e),
                },
            )

            logger.warning(
                f"Returning default type {default_type.__name__} due to JSON error"
            )
            return default_type() if callable(default_type) else default_type

    @staticmethod
    def safe_deserialize(data: Optional[str], default_value: Any = None) -> Any:
        """
        Safely deserialize JSON string without raising exceptions.

        Args:
            data: JSON string to deserialize
            default_value: Value to return if deserialization fails

        Returns:
            Deserialized data or default_value
        """
        if not data:
            return default_value

        try:
            return json.loads(data)
        except (json.JSONDecodeError, TypeError):
            logger.debug(f"Safe JSON deserialization failed, returning default value")
            return default_value


class ModelJSONMixin:
    """Mixin class to add JSON serialization capabilities to SQLModel classes."""

    def to_dict(
        self, exclude_none: bool = True, exclude_fields: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Convert model instance to dictionary.

        Args:
            exclude_none: Whether to exclude None values
            exclude_fields: List of field names to exclude

        Returns:
            Dictionary representation of the model
        """
        exclude_fields = exclude_fields or []
        result = {}

        # Get model fields (works with SQLModel/Pydantic)
        if hasattr(self, "__fields__"):
            fields = self.__fields__.keys()
        elif hasattr(self, "model_fields"):
            fields = self.model_fields.keys()
        else:
            # Fallback to instance attributes
            fields = [attr for attr in dir(self) if not attr.startswith("_")]

        for field_name in fields:
            if field_name in exclude_fields:
                continue

            try:
                value = getattr(self, field_name)

                # Skip None values if requested
                if exclude_none and value is None:
                    continue

                # Handle datetime serialization
                if isinstance(value, datetime):
                    value = value.isoformat()

                result[field_name] = value
            except AttributeError:
                continue

        return result

    def to_json(self, **kwargs) -> str:
        """
        Convert model instance to JSON string.

        Args:
            **kwargs: Arguments passed to to_dict()

        Returns:
            JSON string representation
        """
        return JSONField.serialize(self.to_dict(**kwargs))


def _json_serializer(obj: Any) -> Any:
    """Custom JSON serializer for non-standard types."""
    if isinstance(obj, datetime):
        return obj.isoformat()
    elif hasattr(obj, "to_dict"):
        return obj.to_dict()
    elif hasattr(obj, "__dict__"):
        return obj.__dict__
    else:
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def serialize_list(items: List[Any]) -> Optional[str]:
    return JSONField.serialize(items)


def deserialize_list(data: Optional[str]) -> List[Any]:
    return JSONField.deserialize(data, list)


def serialize_dict(data: Dict[str, Any]) -> Optional[str]:
    return JSONField.serialize(data)


def deserialize_dict(data: Optional[str]) -> Dict[str, Any]:
    return JSONField.deserialize(data, dict)


def serialize_source_chunks(chunks: Optional[List[str]]) -> Optional[str]:
    if not chunks:
        return None
    return JSONField.serialize(chunks)


def deserialize_source_chunks(data: Optional[str]) -> List[str]:
    return JSONField.deserialize(data, list)


def serialize_relevance_scores(scores: Optional[List[float]]) -> Optional[str]:
    if not scores:
        return None
    return JSONField.serialize(scores)


def deserialize_relevance_scores(data: Optional[str]) -> List[float]:
    result = JSONField.deserialize(data, list)
    return [
        float(score) if isinstance(score, (int, float, str)) else 0.0
        for score in result
    ]


def serialize_metadata(metadata: Optional[Dict[str, Any]]) -> Optional[str]:
    if not metadata:
        return None
    return JSONField.serialize(metadata)


def deserialize_metadata(data: Optional[str]) -> Dict[str, Any]:
    return JSONField.deserialize(data, dict)
