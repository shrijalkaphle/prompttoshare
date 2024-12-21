from helpers.db import execute, fetchOne


def fetchSecurityDetail():
    security = fetchOne('SELECT * FROM security')
    if not security:
        execute("INSERT INTO security (profile_rating, problem_report, post, generate) VALUES ('10','10','10','10')")
        security = fetchOne('SELECT * FROM security')
    return security


def updateSecurityDetailByAdmin(id, body):
    security = fetchOne('SELECT * FROM security WHERE id = ' + str(id))
    if not security:
        return {
            "error": True,
            "message": "Security not found"
        }
    
    execute("UPDATE security SET profile_rating='"+ body['profile_rating'] +"', problem_report='"+ body['problem_report'] +"', post='"+ body['post'] +"', generate='"+ body['generate'] +"' WHERE id = " + str(id))

    security = fetchOne('SELECT * FROM security WHERE id = ' + str(id))

    return {
        "error": False,
        "message": "Security updated successfully",
        "security": security
    }
    pass