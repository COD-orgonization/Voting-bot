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
                gender boolean,
                fio TEXT,
                description TEXT,
                photo_id TEXT,
                from_voice text,
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
        
    def update_user(self, user_id: int, fio: str, photo_id: str, gender: bool, description: str = "") -> bool:
        """Добавление нового пользователя"""
        try:
            self.cursor.execute('''
                UPDATE users SET fio=?, photo_id=?, description=?, gender=? WHERE id=?
            ''', (fio, photo_id, description, gender, user_id))
            self.connection.commit()
            return True
        except sqlite3.IntegrityError:
            # Пользователь уже существует
            return False

    def add_user(self, user_id) -> bool:
        try:
            self.cursor.execute('''
                INSERT INTO users (id) 
                VALUES (?)
            ''', (user_id,))
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
                "gender": bool(row[1]),  # Добавлено поле gender
                "fio": row[2],
                "description": row[3],
                "photo_id": row[4],
                "from_voice": row[5],
                "is_voted": bool(row[6]),
                "vote_count": row[7]
            }
        return None
    
    def get_all_users(self, exclude_id: int = None) -> List[Dict[str, Any]]:
        """Получение всех пользователей"""
        if exclude_id:
            self.cursor.execute('SELECT * FROM users WHERE id != ? AND fio IS NOT NULL AND fio != ""', (exclude_id,))
        else:
            self.cursor.execute('SELECT * FROM users where fio IS NOT NULL AND fio != ""')
        
        rows = self.cursor.fetchall()
        users = []
        for row in rows:
            users.append({
                "id": row[0],
                "gender": bool(row[1]),  # Добавлено поле gender
                "fio": row[2],
                "description": row[3],
                "photo_id": row[4],
                "from_voice": row[5],
                "is_voted": bool(row[6]),
                "vote_count": row[7]
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
                "gender": bool(row[1]),
                "fio": row[2],
                "description": row[3],
                "photo_id": row[4],
                "from_voice": row[5],
                "is_voted": bool(row[6]),
                "vote_count": row[7]
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
                UPDATE users SET is_voted = 1, from_voice = ? WHERE id = ?
            ''', (target_id, voter_id,))
            
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
    
    def delete_user(self, user_id: int):
        """Удаление пользователя с аннулированием связанных голосов"""
        try:
            # 1. Получаем информацию о том, за кого голосовал удаляемый пользователь
            self.cursor.execute('SELECT from_voice FROM users WHERE id = ?', (user_id,))
            row = self.cursor.fetchone()
            
            if row and row[0]:  # Если пользователь голосовал за кого-то
                target_id = row[0]
                # Уменьшаем счетчик голосов у цели
                self.cursor.execute('''
                    UPDATE users SET vote_count = vote_count - 1 
                    WHERE id = ? AND vote_count > 0
                ''', (target_id,))
            
            # 2. Находим всех, кто голосовал за удаляемого пользователя
            self.cursor.execute('SELECT id FROM users WHERE from_voice = ?', (user_id,))
            voters = self.cursor.fetchall()
            
            # Сбрасываем статус голосования у тех, кто голосовал за удаляемого
            for voter in voters:
                voter_id = voter[0]
                self.cursor.execute('''
                    UPDATE users SET is_voted = 0, from_voice = NULL 
                    WHERE id = ?
                ''', (voter_id,))
            
            # 3. Удаляем пользователя
            self.cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
            self.add_user(user_id)
            
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error deleting user: {e}")
            self.connection.rollback()
            return False

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