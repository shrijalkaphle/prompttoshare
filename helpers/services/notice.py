from helpers.db import execute, fetchAll, fetchOne


def fetchAllNotices(perPage, page):
    offset = (page - 1) * perPage
    notices = fetchAll("SELECT * FROM notice ORDER BY id DESC LIMIT " + str(perPage) + " OFFSET " + str(offset))

    total = fetchOne("SELECT count(*) as total FROM notice")['total']
    response = {
        "page_number": page,
        "page_size": len(notices),
        "total_data": total,
        "data": notices,
    }
    return response

def createNotice(body):
    execute("INSERT INTO notice (name, created_at) VALUES ('"+ str(body['name']) +"', NOW())")
    notice = fetchOne("SELECT * FROM notice ORDER BY id DESC LIMIT 1")
    return {
        "error": False,
        "message": "Notice created successfully",
        "notice": notice
    }


def editNotice(noticeId, body):
    notice = fetchOne("SELECT * FROM notice WHERE id = '" + str(noticeId) + "'")

    if not notice:
        return {
            "error": True,
            "message": "Notice not found"
        }
    
    execute("UPDATE notice SET name = '"+ str(body['name']) +"' WHERE id = '" + str(noticeId) + "'")

    notice = fetchOne("SELECT * FROM notice WHERE id = '" + str(noticeId) + "'")
    return {
        "error": False,
        "message": "Notice updated successfully",
        "notice": notice
    }

def deleteNotice(noticeId):
    notice = fetchOne("SELECT * FROM notice WHERE id = '" + str(noticeId) + "'")

    if not notice:
        return {
            "error": True,
            "message": "Notice not found"
        }
    
    execute("DELETE FROM notice WHERE id = '" + str(noticeId) + "'")

    return {
        "error": False,
        "message": "Notice deleted successfully"
    }