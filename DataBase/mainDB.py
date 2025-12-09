# mainDB.py
import sqlite3
from typing import Optional, Dict, Any, List

class UserDB:
    def __init__(self, db_name: str = "dataBase.db"):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        """Создание таблиц если они не существуют"""
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                fio TEXT NOT NULL,
                description TEXT,
                photo_id TEXT NOT NULL,
                is_voted BOOLEAN DEFAULT 0,
                vote_count INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value BOOLEAN DEFAULT 0
            )
        ''')
        self.connection.commit()
        
        self.cursor.execute('''
            INSERT OR IGNORE INTO settings (key, value) 
            VALUES ('voting_enabled', false)
        ''')
        self.connection.commit()
        
    def add_user(self, user_id: int, fio: str, photo_id: str, description: str = "") -> bool:
        """Добавление нового пользователя"""
        try:
            self.cursor.execute('''
                INSERT INTO users (id, fio, photo_id, description) 
                VALUES (?, ?, ?, ?)
            ''', (user_id, fio, photo_id, description))
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            # Пользователь уже существует
            return False
            
    def get_user(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получение информации о пользователе"""
        self.cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        row = self.cursor.fetchone()
        
        if row:
            return {
                "id": row[0],
                "fio": row[1],
                "description": row[2],
                "photo_id": row[3],
                "is_voted": bool(row[4]),
                "vote_count": row[5]
            }
        return None
        
    def get_all_users(self, exclude_id: int = None) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        if exclude_id:
            self.cursor.execute('SELECT * FROM users WHERE id != ?', (exclude_id,))
        else:
            self.cursor.execute('SELECT * FROM users')
        
        rows = self.cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "fio": row[1],
                "description": row[2],
                "photo_id": row[3],
                "is_voted": bool(row[4]),
                "vote_count": row[5]
            })
        return users
        
    def get_users_for_voting(self, exclude_id: int = None) -> List[Dict[str, Any]]:
        """Получение пользователей для голосования"""
        query = 'SELECT * FROM users WHERE id != ?'
        params = [exclude_id]
            
        self.cursor.execute(query, params)
        rows = self.cursor.fetchall()
        
        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "fio": row[1],
                "description": row[2],
                "photo_id": row[3],
                "is_voted": bool(row[4]),
                "vote_count": row[5]
            })
        return users
        
    def process_vote(self, voter_id: int, target_id: int) -> bool:
        """Обработка голосования"""
        try:
            # Проверяем, голосовал ли уже пользователь
            self.cursor.execute('SELECT is_voted FROM users WHERE id = ?', (voter_id,))
            voter = self.cursor.fetchone()
            
            if not voter or voter[0]:  # Пользователь не найден или уже голосовал
                return False
                
            # Обновляем статус голосовавшего
            self.cursor.execute('''
                UPDATE users SET is_voted = 1 WHERE id = ?
            ''', (voter_id,))
            
            # Увеличиваем счетчик голосов у цели
            self.cursor.execute('''
                UPDATE users SET vote_count = vote_count + 1 WHERE id = ?
            ''', (target_id,))
            
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error processing vote: {e}")
            return False
            
    def has_user_voted(self, user_id: int) -> bool:
        """Проверяет, голосовал ли пользователь"""
        user = self.get_user(user_id)
        return user['is_voted'] if user else False
        
    def get_user_vote_count(self, user_id: int) -> int:
        """Получает количество голосов пользователя"""
        user = self.get_user(user_id)
        return user['vote_count'] if user else 0

    def reset_votes(self):
        self.cursor.execute('UPDATE users SET is_voted = 0, vote_count = 0')
        self.connection.commit()

    def is_voting_enabled(self) -> bool:
        """Проверяет, активно ли голосование"""
        self.cursor.execute('SELECT value FROM settings WHERE key = ?', ('voting_enabled',))
        result = self.cursor.fetchone()
        return result[0]
        
    def set_voting_enabled(self, enabled: bool) -> bool:
        """Включает или выключает голосование"""
        try:
            self.cursor.execute('''
                INSERT OR REPLACE INTO settings (key, value) 
                VALUES ('voting_enabled', ?)
            ''', (enabled,))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error setting voting state: {e}")
            return False

    def __del__ (self):
        """Закрытие соединения с БД"""
        self.connection.close()