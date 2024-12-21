
from helpers.db import execute, fetchOne
from helpers.services.user import getAllUser


def calculateLevel():
    totalUser = fetchOne('SELECT COUNT(*) as total FROM user')['total']
    user = getAllUser(totalUser, 1)['data']

    # filter out users with zero trophy
    filteredUser = [user for user in user if user['trophy'] != 0]

    sortedUser = sorted(filteredUser, key=lambda x: x['trophy'], reverse=False)

    # Assign levels based on wealth
    levels_assigned = []
    totalRankableUser = len(sortedUser)

    for i, user in enumerate(sortedUser, start=1):
        level = int((i / totalRankableUser) * 10)
        execute(f"UPDATE level SET level = {level} WHERE user_id = {user['user_id']}")
        user_with_level = {
            "user_id": user["user_id"],
            "level": level
        }
        levels_assigned.append(user_with_level)


    print(levels_assigned)

    return levels_assigned