import sqlite3
from typing import Optional, Dict, Any, List

class UserDB:
    def __init__(self, db_name: str = "dataBase.db"):
        self.connection = sqlite3.connect(db_name, check_same_thread=False)
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        """Создание таблиц если они не существуют"""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY,
                    gender boolean,
                    fio TEXT,
                    description TEXT,
                    photo_id TEXT,
                    from_voice_prince text,
                    from_voice_princess text,            
                    voted_for_prince BOOLEAN DEFAULT 0,
                    voted_for_princess BOOLEAN DEFAULT 0,
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
        except sqlite3.IntegrityError as e:
            print(f"Error table: {e}")
        
    def update_user(self, user_id: int, fio: str, photo_id: str, gender: bool, description: str = "") -> bool:
        """Добавление нового пользователя"""
        try:
            # Проверяем, существует ли пользователь
            existing_user = self.get_user(user_id)
            
            if existing_user:
                # Пользователь существует - обновляем данные
                self.cursor.execute('''
                    UPDATE users SET fio=?, photo_id=?, description=?, gender=? WHERE id=?
                ''', (fio, photo_id, description, gender, user_id))
            else:
                # Пользователь не существует - создаем нового
                self.cursor.execute('''
                    INSERT INTO users (id, fio, photo_id, description, gender) VALUES (?, ?, ?, ?, ?)
                ''', (user_id, fio, photo_id, description, gender))
            
            self.connection.commit()
            return True
        except sqlite3.Error as e:
            # Обработка всех возможных ошибок SQLite
            print(f"Ошибка при работе с базой данных: {e}")
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
        self.connection.commit()
        
        if row:
            return {
                "id": row[0],
                "gender": bool(row[1]),
                "fio": row[2],
                "description": row[3],
                "photo_id": row[4],
                "from_voice_prince": row[5],
                "from_voice_princess": row[6],
                "voted_for_prince": bool(row[7]),
                "voted_for_princess": bool(row[8]),
                "vote_count": row[9]
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
                "gender": bool(row[1]),
                "fio": row[2],
                "description": row[3],
                "photo_id": row[4],
                "from_voice_prince": row[5],
                "from_voice_princess": row[6],
                "voted_for_prince": bool(row[7]),
                "voted_for_princess": bool(row[8]),
                "vote_count": row[9]
            })
        self.connection.commit()
        return users

    def get_users_for_voting(self, exclude_id: int = None, gender: bool = None) -> List[Dict[str, Any]]:
        """Получение пользователей для голосования"""
        query = 'SELECT * FROM users WHERE id != ? AND fio IS NOT NULL AND fio != ""'
        params = [exclude_id]
        
        if gender is not None:
            query += ' AND gender = ?'
            params.append(gender)
            
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
                "from_voice_prince": row[5],
                "from_voice_princess": row[6],
                "voted_for_prince": bool(row[7]),
                "voted_for_princess": bool(row[8]),
                "vote_count": row[9]
            })
        self.connection.commit()
        return users
        
    def process_vote(self, voter_id: int, target_id: int, vote_for_prince: bool = True) -> bool:
        """Обработка голосования"""
        try:
            # Получаем информацию о голосующем и цели
            voter = self.get_user(voter_id)
            target = self.get_user(target_id)
            
            if not voter or not target:
                return False
                
            # Проверяем, голосовал ли уже пользователь
            if vote_for_prince:
                if voter["voted_for_prince"]:
                    return False
                # Обновляем статус голосовавшего
                self.cursor.execute('''
                    UPDATE users SET voted_for_prince = 1, from_voice_prince = ? WHERE id = ?
                ''', (target_id, voter_id,))
            else:
                if voter["voted_for_princess"]:
                    return False
                # Обновляем статус голосовавшего
                self.cursor.execute('''
                    UPDATE users SET voted_for_princess = 1, from_voice_princess = ? WHERE id = ?
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
            
    def has_user_voted(self, user_id: int, vote_for_prince: bool = True) -> bool:
        """Проверяет, голосовал ли пользователь"""
        user = self.get_user(user_id)
        if not user:
            return False
            
        if vote_for_prince:
            return user['voted_for_prince']
        else:
            return user['voted_for_princess']
        
    def get_user_vote_count(self, user_id: int) -> int:
        """Получает количество голосов пользователя"""
        user = self.get_user(user_id)
        return user['vote_count'] if user else 0

    def reset_votes(self):
        """Сброс всех голосов"""
        self.cursor.execute('''
            UPDATE users SET 
                voted_for_prince = 0, 
                voted_for_princess = 0,
                from_voice_prince = NULL,
                from_voice_princess = NULL,
                vote_count = 0
        ''')
        self.connection.commit()
    
    def reset_user_votes(self, user_id: str) -> bool:
        try:
            user = self.get_user(user_id)

            if user["from_voice_prince"]:
                target_id = user["from_voice_prince"]
                # Уменьшаем счетчик голосов у цели
                self.cursor.execute('''
                    UPDATE users SET vote_count = vote_count - 1 
                    WHERE id = ? AND vote_count > 0
                ''', (target_id,))
            
            if user["from_voice_princess"]:
                target_id = user["from_voice_princess"]
                # Уменьшаем счетчик голосов у цели
                self.cursor.execute('''
                    UPDATE users SET vote_count = vote_count - 1 
                    WHERE id = ? AND vote_count > 0
                ''', (target_id,))

            self.cursor.execute('''
            UPDATE users SET 
                voted_for_prince = 0, 
                voted_for_princess = 0,
                from_voice_prince = NULL,
                from_voice_princess = NULL
                WHERE id=?
            ''', (user_id,))
            self.connection.commit()
            return True
        except Exception as e:
            print(f"Error: {e}")
            return False

    def delete_user(self, user_id: int):
        """Удаление пользователя с аннулированием связанных голосов"""
        try:
            # 1. Получаем информацию о том, за кого голосовал удаляемый пользователь
            user = self.get_user(user_id)
            
            if not user:
                return False
                
            # 2. Обрабатываем голоса за принца
            if user["from_voice_prince"]:
                target_id = user["from_voice_prince"]
                # Уменьшаем счетчик голосов у цели
                self.cursor.execute('''
                    UPDATE users SET vote_count = vote_count - 1 
                    WHERE id = ? AND vote_count > 0
                ''', (target_id,))
            
            # 3. Обрабатываем голоса за принцессу
            if user["from_voice_princess"]:
                target_id = user["from_voice_princess"]
                # Уменьшаем счетчик голосов у цели
                self.cursor.execute('''
                    UPDATE users SET vote_count = vote_count - 1 
                    WHERE id = ? AND vote_count > 0
                ''', (target_id,))
            
            # 4. Находим всех, кто голосовал за удаляемого пользователя (как принца)
            self.cursor.execute('SELECT id FROM users WHERE from_voice_prince = ?', (user_id,))
            prince_voters = self.cursor.fetchall()
            
            # Сбрасываем статус голосования у тех, кто голосовал за удаляемого как принца
            for voter in prince_voters:
                voter_id = voter[0]
                self.cursor.execute('''
                    UPDATE users SET voted_for_prince = 0, from_voice_prince = NULL 
                    WHERE id = ?
                ''', (voter_id,))
            
            # 5. Находим всех, кто голосовал за удаляемого пользователя (как принцессу)
            self.cursor.execute('SELECT id FROM users WHERE from_voice_princess = ?', (user_id,))
            princess_voters = self.cursor.fetchall()
            
            # Сбрасываем статус голосования у тех, кто голосовал за удаляемого как принцессу
            for voter in princess_voters:
                voter_id = voter[0]
                self.cursor.execute('''
                    UPDATE users SET voted_for_princess = 0, from_voice_princess = NULL 
                    WHERE id = ?
                ''', (voter_id,))
            
            # 6. Удаляем пользователя и создаем запись с минимальными данными
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
        self.connection.commit()
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

db = UserDB()