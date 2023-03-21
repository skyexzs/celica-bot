import sqlite3
from sqlite3 import Error
from config import MAIN_PATH
from typing import List
import os

class SQLiteDB():
    @staticmethod
    def create_connection(db_file):
        conn = None
        try:
            conn = sqlite3.connect(db_file)
            #print(sqlite3.version)
        except Error as e:
            print(e)
        
        return conn

    @staticmethod
    def add_bosses(conn: sqlite3.Connection, bosses=List[str], commit=False):
        try:
            query = f''' INSERT OR IGNORE INTO bosses(boss_name)
                        VALUES({"),(".join(["?"]*len(bosses))}) '''
            cur = conn.cursor()
            cur.execute(query, bosses)
            if commit: conn.commit()
        except Error as e:
            raise e

    def insert_records(conn: sqlite3.Connection, data:List[dict], commit=False):
        try:
            for d in data:
                query = f''' INSERT OR IGNORE INTO boss_score(boss_id, start_of_week, rank, difficulty, time, score)
                            SELECT bosses.boss_id, "{d['start_of_week']}", "{d['rank']}", "{d['diff']}", "{d['time']}", {d['score']}
                            FROM bosses WHERE boss_name=="{d['boss']}" '''
                cur = conn.cursor()
                cur.execute(query)
                if commit: conn.commit()
        except Error as e:
            raise e

# if __name__ == "__main__":
#     conn = create_connection(os.path.join(MAIN_PATH, "database", "exppc.db"))
#     add_bosses(conn, ["Luarbiasa"])
#     add_bosses(conn, ["Luna","LoL","Wow","Dongdong"])
#     insert_record(conn, [{'boss':'Luna','start_of_week':'2023/10/12','rank':'S+','diff':'Test', 'time':'0:01', 'score':192800},
#                          {'boss':'Test','start_of_week':'2023/05/12','rank':'SSS','diff':'Elite','time':'0:02', 'score':501230}])
#     conn.close()