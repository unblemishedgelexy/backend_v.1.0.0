from .mongo import get_db

db = get_db()

users_col = db.users
communities_col = db.communities
groups_col = db.groups
messages_col = db.messages
dm_keys_col = db.dm_keys
