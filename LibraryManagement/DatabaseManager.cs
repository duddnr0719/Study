using MySql.Data.MySqlClient;

namespace LibraryManagement
{
    /// <summary>
    /// MySQL 연결 및 테이블 자동 생성 관리자
    /// 접속: root / 1111  /  DB: sch
    /// </summary>
    public static class DatabaseManager
    {
        private const string Server   = "localhost";
        private const string DbName   = "sch";
        private const string User     = "root";
        private const string Password = "1111";

        public static string ConnectionString =>
            $"Server={Server};Database={DbName};Uid={User};Pwd={Password};" +
            "CharSet=utf8mb4;SslMode=None;AllowUserVariables=True;";

        /// <summary>열린 MySqlConnection 반환</summary>
        public static MySqlConnection GetConnection()
        {
            var conn = new MySqlConnection(ConnectionString);
            conn.Open();
            return conn;
        }

        /// <summary>
        /// 프로그램 시작 시 호출.
        /// sch 데이터베이스와 book / user / borrow 테이블을 없으면 자동 생성.
        /// </summary>
        public static void InitializeDatabase()
        {
            // DB 없이 서버 접속 → sch 생성
            string serverConn =
                $"Server={Server};Uid={User};Pwd={Password};CharSet=utf8mb4;SslMode=None;";

            using var conn = new MySqlConnection(serverConn);
            conn.Open();
            using var cmd = conn.CreateCommand();

            cmd.CommandText =
                "CREATE DATABASE IF NOT EXISTS sch " +
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;";
            cmd.ExecuteNonQuery();

            cmd.CommandText = "USE sch;";
            cmd.ExecuteNonQuery();

            // ── book 테이블 ──────────────────────────────────────────────
            // isbn 을 PK 로 사용 (교재 원본과 동일하게 사용자 직접 입력)
            // 대출 정보(is_borrowed, borrowed_at, user_id, user_name)도 book 테이블에 내장
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS book (
                    isbn        VARCHAR(20)  PRIMARY KEY,
                    name        VARCHAR(200) NOT NULL,
                    publisher   VARCHAR(100) DEFAULT '',
                    page        INT          DEFAULT 0,
                    is_borrowed TINYINT(1)   DEFAULT 0,
                    borrowed_at DATETIME,
                    user_id     INT          DEFAULT 0,
                    user_name   VARCHAR(50)  DEFAULT ''
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
            cmd.ExecuteNonQuery();

            // ── user 테이블 ──────────────────────────────────────────────
            // id 는 사용자가 직접 입력 (auto_increment 아님)
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS user (
                    id   INT         PRIMARY KEY,
                    name VARCHAR(50) NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
            cmd.ExecuteNonQuery();

            // ── borrow 테이블 ────────────────────────────────────────────
            // 대출 이력 로그 (과제 요건의 3번째 테이블)
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS borrow (
                    borrow_id   INT AUTO_INCREMENT PRIMARY KEY,
                    isbn        VARCHAR(20) NOT NULL,
                    user_id     INT         NOT NULL,
                    borrowed_at DATETIME    NOT NULL,
                    returned_at DATETIME,
                    is_returned TINYINT(1)  DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
            cmd.ExecuteNonQuery();
        }
    }
}
