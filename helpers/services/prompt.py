import math
from helpers.db import execute, fetchAll, fetchOne


def fetchAllPrompts(perPage, page):
    offset = (page - 1) * perPage
    prompts = fetchAll("SELECT * FROM prompt ORDER BY id DESC LIMIT " + str(perPage) + " OFFSET " + str(offset))

    total = fetchOne("SELECT count(*) as total FROM prompt")['total']
    response = {
        "page_number": page,
        "page_size": len(prompts),
        "total_data": total,
        "data": prompts,
        "total_page": math.ceil(total / perPage)
    }
    return response

def createPrompt(body):
    execute("INSERT INTO prompt (name, created_at) VALUES ('"+ str(body['name']) +"', NOW())")

    prompt = fetchOne("SELECT * FROM prompt ORDER BY id DESC LIMIT 1")
    return {
        "error": False,
        "message": "Prompt created successfully",
        "prompt": prompt
    }


def editPrompt(promptId, body):
    prompt = fetchOne("SELECT * FROM prompt WHERE id = '" + str(promptId) + "'")

    if not prompt:
        return {
            "error": True,
            "message": "Prompt not found"
        }
    
    execute("UPDATE prompt SET name = '"+ str(body['name']) +"' WHERE id = '" + str(promptId) + "'")
    prompt = fetchOne("SELECT * FROM prompt WHERE id = '" + str(promptId) + "'")
    return {
        "error": False,
        "message": "Prompt updated successfully",
        "prompt": prompt
    }

def deletePrompt(promptId):
    prompt = fetchOne("SELECT * FROM prompt WHERE id = '" + str(promptId) + "'")

    if not prompt:
        return {
            "error": True,
            "message": "Prompt not found"
        }
    
    execute("DELETE FROM prompt WHERE id = '" + str(promptId) + "'")

    return {
        "error": False,
        "message": "Prompt deleted successfully"
    }