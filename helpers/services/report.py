from helpers.db import fetchAll, fetchOne


def fetchAllReports(perPage, page):
    offset = (page - 1) * perPage
    reports = fetchAll("SELECT report.*,user.name,user.email FROM report LEFT JOIN user ON report.user_id = user.user_id ORDER BY id DESC LIMIT " + str(perPage) + " OFFSET " + str(offset))

    total = fetchOne("SELECT count(*) as total FROM report")['total']
    response = {
        "page_number": page,
        "page_size": len(reports),
        "total_data": total,
        "data": reports,
    }
    return response
