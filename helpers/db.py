from flask_mysqldb import MySQL
import MySQLdb.cursors

mysql = MySQL()

def init_app(app):
    mysql.init_app(app)

def get_db():
    return mysql.connection

def fetchAll(query):
    cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query)
    data = cursor.fetchall()
    cursor.close()
    return data

def fetchOne(query):
    cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query)
    data = cursor.fetchone()
    cursor.close()
    return data

def execute(query):
    cursor = get_db().cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query)
    get_db().commit()
    cursor.close()