using MySql.Data.MySqlClient;
using LibraryManagement.Models;

namespace LibraryManagement
{
    /// <summary>
    /// 데이터 관리자 (교재 원본 DataManager 구조 유지)
    ///
    /// 원본 XML 방식:
    ///   Load()  → File.ReadAllText + XElement.Parse
    ///   Save()  → File.WriteAllText (전체 덮어쓰기)
    ///
    /// 변경 MySQL 방식:
    ///   Load()  → SELECT * FROM book / user
    ///   Save()  → DELETE + INSERT (전체 동기화, 원본과 동일한 흐름)
    /// </summary>
    public static class DataManager
    {
        public static List<Book> Books { get; private set; } = new();
        public static List<User> Users { get; private set; } = new();

        // ── Load ─────────────────────────────────────────────────────────
        /// <summary>
        /// MySQL에서 도서·사용자 목록을 읽어 메모리 리스트에 적재.
        /// 원본의 File.ReadAllText + XElement.Parse 대체.
        /// </summary>
        public static void Load()
        {
            Books = new List<Book>();
            Users = new List<User>();

            using var conn = DatabaseManager.GetConnection();

            // book 목록
            using (var cmd = new MySqlCommand("SELECT * FROM book ORDER BY isbn", conn))
            using (var r = cmd.ExecuteReader())
            {
                while (r.Read())
                {
                    Books.Add(new Book
                    {
                        Isbn       = r.GetString("isbn"),
                        Name       = r.GetString("name"),
                        Publisher  = r.IsDBNull(r.GetOrdinal("publisher")) ? "" : r.GetString("publisher"),
                        Page       = r.GetInt32("page"),
                        isBorrowed = r.GetBoolean("is_borrowed"),
                        BorrowedAt = r.IsDBNull(r.GetOrdinal("borrowed_at"))
                                        ? new DateTime()
                                        : r.GetDateTime("borrowed_at"),
                        UserId   = r.GetInt32("user_id"),
                        UserName = r.IsDBNull(r.GetOrdinal("user_name")) ? "" : r.GetString("user_name")
                    });
                }
            }

            // user 목록
            using (var cmd = new MySqlCommand("SELECT * FROM user ORDER BY id", conn))
            using (var r = cmd.ExecuteReader())
            {
                while (r.Read())
                {
                    Users.Add(new User
                    {
                        Id   = r.GetInt32("id"),
                        Name = r.GetString("name")
                    });
                }
            }
        }

        // ── Save ─────────────────────────────────────────────────────────
        /// <summary>
        /// 메모리 리스트를 MySQL에 전체 동기화.
        /// 원본의 File.WriteAllText (전체 덮어쓰기) 대체.
        /// </summary>
        public static void Save()
        {
            using var conn = DatabaseManager.GetConnection();
            using var tx   = conn.BeginTransaction();

            try
            {
                // ── book 동기화
                new MySqlCommand("DELETE FROM book", conn, tx).ExecuteNonQuery();

                foreach (var b in Books)
                {
                    using var cmd = new MySqlCommand(@"
                        INSERT INTO book
                            (isbn, name, publisher, page,
                             is_borrowed, borrowed_at, user_id, user_name)
                        VALUES
                            (@isbn, @name, @publisher, @page,
                             @isBorrowed, @borrowedAt, @userId, @userName)",
                        conn, tx);

                    cmd.Parameters.AddWithValue("@isbn",       b.Isbn);
                    cmd.Parameters.AddWithValue("@name",       b.Name);
                    cmd.Parameters.AddWithValue("@publisher",  b.Publisher);
                    cmd.Parameters.AddWithValue("@page",       b.Page);
                    cmd.Parameters.AddWithValue("@isBorrowed", b.isBorrowed ? 1 : 0);
                    cmd.Parameters.AddWithValue("@borrowedAt",
                        b.isBorrowed ? (object)b.BorrowedAt : DBNull.Value);
                    cmd.Parameters.AddWithValue("@userId",   b.UserId);
                    cmd.Parameters.AddWithValue("@userName", b.UserName);
                    cmd.ExecuteNonQuery();
                }

                // ── user 동기화
                new MySqlCommand("DELETE FROM user", conn, tx).ExecuteNonQuery();

                foreach (var u in Users)
                {
                    using var cmd = new MySqlCommand(
                        "INSERT INTO user (id, name) VALUES (@id, @name)", conn, tx);
                    cmd.Parameters.AddWithValue("@id",   u.Id);
                    cmd.Parameters.AddWithValue("@name", u.Name);
                    cmd.ExecuteNonQuery();
                }

                tx.Commit();
            }
            catch
            {
                tx.Rollback();
                throw;
            }
        }

        // ── borrow 테이블 로그 ────────────────────────────────────────────

        /// <summary>대출 시 borrow 테이블에 이력 삽입</summary>
        public static void LogBorrow(string isbn, int userId, DateTime borrowedAt)
        {
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(@"
                INSERT INTO borrow (isbn, user_id, borrowed_at)
                VALUES (@isbn, @userId, @borrowedAt)", conn);
            cmd.Parameters.AddWithValue("@isbn",       isbn);
            cmd.Parameters.AddWithValue("@userId",     userId);
            cmd.Parameters.AddWithValue("@borrowedAt", borrowedAt);
            cmd.ExecuteNonQuery();
        }

        /// <summary>반납 시 borrow 테이블 최신 미반납 행 업데이트</summary>
        public static void LogReturn(string isbn)
        {
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(@"
                UPDATE borrow
                   SET is_returned = 1,
                       returned_at = @now
                 WHERE isbn        = @isbn
                   AND is_returned = 0
                 ORDER BY borrowed_at DESC
                 LIMIT 1", conn);
            cmd.Parameters.AddWithValue("@now",  DateTime.Now);
            cmd.Parameters.AddWithValue("@isbn", isbn);
            cmd.ExecuteNonQuery();
        }
    }
}
