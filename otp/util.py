def getPuppetChannel(avatarId: int) -> int:
    """Returns the channel for the associated avatar id."""
    return avatarId + (1001 << 32)


def getAccountChannel(dislId: int) -> int:
    """Returns the channel for the associated DISL id."""
    return dislId + (1003 << 32)


def getClientSenderChannel(dislId: int, avatarId: int) -> int:
    """
    Returns the channel for the associated DISL id and avatar id.
    This is the sender channel the client agent will use for authenticated clients.
    """
    return dislId << 32 | avatarId


def getAccountIDFromChannel(sender: int) -> int:
    """Returns the account/disl id from a client agent sender channel."""
    return sender >> 32


def getAvatarIDFromChannel(sender: int) -> int:
    """Returns the avatar id (if present) from a client agent sender channel."""
    return sender & 0xFFFFFFFF
