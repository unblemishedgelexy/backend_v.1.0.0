from .collections import messages_col, groups_col

messages_col.create_index([("roomId", 1), ("createdAt", -1)])
groups_col.create_index("communityId")
