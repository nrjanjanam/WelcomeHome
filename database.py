import pymysql
import pymysql.cursors
from config import Config
from werkzeug.security import check_password_hash
import hashlib

def get_db():
    configObj = Config()
    return pymysql.connect(
        host= configObj.MYSQL_HOST,
        user= configObj.MYSQL_USER,
        password= configObj.MYSQL_PASSWORD,
        db= configObj.MYSQL_DB,
        charset='utf8mb4',
        cursorclass= pymysql.cursors.DictCursor
    )
    
def hash_password(password, salt):
    return hashlib.sha256(f"{password}{salt}".encode()).hexdigest()