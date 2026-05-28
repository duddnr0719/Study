using MySql.Data.MySqlClient;

namespace LibraryManagement.Database
{
    /// <summary>
    /// MySQL 데이터베이스 연결 및 초기화 관리자
    /// 접속 정보: root / 1111, DB: sch
    /// </summary>
    public static class DatabaseManager
    {
        private const string Server   = "localhost";
        private const string Database = "sch";
        private const string UserId   = "root";
        private const string Password = "1111";

        // sch 데이터베이스에 직접 연결하는 커넥션 스트링
        public static string ConnectionString =>
            $"Server={Server};Database={Database};Uid={UserId};Pwd={Password};" +
            $"CharSet=utf8mb4;AllowUserVariables=True;SslMode=None;";

        /// <summary>열린 MySqlConnection을 반환합니다.</summary>
        public static MySqlConnection GetConnection()
        {
            var conn = new MySqlConnection(ConnectionString);
            conn.Open();
            return conn;
        }

        /// <summary>
        /// 프로그램 시작 시 호출 — 없으면 DB와 테이블을 자동 생성합니다.
        /// </summary>
        public static void InitializeDatabase()
        {
            // 1) DB 없이 서버에 먼저 접속해서 스키마 생성
            string serverConnectionString =
                $"Server={Server};Uid={UserId};Pwd={Password};" +
                $"CharSet=utf8mb4;SslMode=None;";

            using var initConn = new MySqlConnection(serverConnectionString);
            initConn.Open();

            using var cmd = initConn.CreateCommand();

            // sch 데이터베이스 생성
            cmd.CommandText =
                "CREATE DATABASE IF NOT EXISTS sch " +
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;";
            cmd.ExecuteNonQuery();

            cmd.CommandText = "USE sch;";
            cmd.ExecuteNonQuery();

            // 2) book 테이블
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS book (
                    book_id      INT AUTO_INCREMENT PRIMARY KEY,
                    title        VARCHAR(200) NOT NULL,
                    author       VARCHAR(100) DEFAULT '',
                    publisher    VARCHAR(100) DEFAULT '',
                    isbn         VARCHAR(20)  DEFAULT '',
                    is_available TINYINT(1)   DEFAULT 1
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
            cmd.ExecuteNonQuery();

            // 3) user 테이블
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS user (
                    user_id INT AUTO_INCREMENT PRIMARY KEY,
                    name    VARCHAR(50)  NOT NULL,
                    phone   VARCHAR(20)  DEFAULT '',
                    email   VARCHAR(100) DEFAULT ''
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
            cmd.ExecuteNonQuery();

            // 4) borrow 테이블 (book, user 외래키)
            cmd.CommandText = @"
                CREATE TABLE IF NOT EXISTS borrow (
                    borrow_id   INT AUTO_INCREMENT PRIMARY KEY,
                    book_id     INT  NOT NULL,
                    user_id     INT  NOT NULL,
                    borrow_date DATE NOT NULL,
                    return_date DATE,
                    is_returned TINYINT(1) DEFAULT 0,
                    FOREIGN KEY (book_id) REFERENCES book(book_id),
                    FOREIGN KEY (user_id) REFERENCES user(user_id)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;";
            cmd.ExecuteNonQuery();
        }
    }
}
