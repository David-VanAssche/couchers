"""
Utility functions for the Unified Moderation System (UMS)
"""

from collections.abc import Callable

from sqlalchemy.orm import Session

from couchers.metrics import observe_moderation_action, observe_moderation_queue_item_created
from couchers.models import (
    ModerationAction,
    ModerationLog,
    ModerationObjectType,
    ModerationQueueItem,
    ModerationState,
    ModerationTrigger,
    ModerationVisibility,
)


def create_moderation(
    session: Session,
    object_type: ModerationObjectType,
    object_id: int | Callable[[int], int],
    creator_user_id: int,
) -> ModerationState:
    """
    Creates a ModerationState with SHADOWED visibility and adds to the moderation queue.

    Args:
        session: Database session
        object_type: Type of object being moderated
        object_id: Either the object's ID directly, or a callback that receives
                   moderation_state_id and returns the object_id. Use a callback
                   when the object requires moderation_state_id during creation
                   (e.g., FriendRelationship).
        creator_user_id: ID of the user creating the object

    Example with direct ID:
        moderation_state = create_moderation(session, ModerationObjectType.GROUP_CHAT, chat.id, user_id)

    Example with callback (for circular dependency):
        def create_friend_request(moderation_state_id):
            fr = FriendRelationship(..., moderation_state_id=moderation_state_id)
            session.add(fr)
            session.flush()
            return fr.id

        moderation_state = create_moderation(
            session, ModerationObjectType.FRIEND_REQUEST, create_friend_request, user_id
        )
    """
    # Handle callback pattern for circular dependencies
    if callable(object_id):
        moderation_state = ModerationState(
            object_type=object_type,
            object_id=0,  # Placeholder
            visibility=ModerationVisibility.SHADOWED,
        )
        session.add(moderation_state)
        session.flush()

        # Call the callback to create the object and get its ID
        actual_object_id = object_id(moderation_state.id)
        moderation_state.object_id = actual_object_id
    else:
        moderation_state = ModerationState(
            object_type=object_type,
            object_id=object_id,
            visibility=ModerationVisibility.SHADOWED,
        )
        session.add(moderation_state)
        session.flush()

    session.add(
        ModerationLog(
            moderation_state_id=moderation_state.id,
            action=ModerationAction.CREATE,
            moderator_user_id=creator_user_id,
            new_visibility=ModerationVisibility.SHADOWED,
            reason="Object created.",
        )
    )

    session.add(
        ModerationQueueItem(
            moderation_state_id=moderation_state.id,
            trigger=ModerationTrigger.INITIAL_REVIEW,
            reason="Object created.",
        )
    )
    session.flush()

    observe_moderation_action(ModerationAction.CREATE, object_type)
    observe_moderation_queue_item_created(ModerationTrigger.INITIAL_REVIEW, object_type)

    return moderation_state


def approve_moderation(
    session: Session,
    moderation_state: ModerationState,
    approver_user_id: int,
    reason: str = "Approved.",
) -> None:
    """
    Approves a moderation state, making the content VISIBLE.

    Args:
        session: Database session
        moderation_state: The moderation state to approve
        approver_user_id: ID of the user approving (typically a moderator)
        reason: Reason for approval
    """
    moderation_state.visibility = ModerationVisibility.VISIBLE

    session.add(
        ModerationLog(
            moderation_state_id=moderation_state.id,
            action=ModerationAction.APPROVE,
            moderator_user_id=approver_user_id,
            new_visibility=ModerationVisibility.VISIBLE,
            reason=reason,
        )
    )
    session.flush()

    observe_moderation_action(ModerationAction.APPROVE, moderation_state.object_type)
