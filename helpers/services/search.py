from helpers.services.post import searchPost
from helpers.services.user import searchUser


def searchAll(searchQuery, currentUserId):
    return {
        "users": searchUser(searchQuery, currentUserId),
        "posts": searchPost(searchQuery, currentUserId)
    }