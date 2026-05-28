using MySql.Data.MySqlClient;
using LibraryManagement.Database;
using LibraryManagement.Models;

namespace LibraryManagement.Repositories
{
    /// <summary>book 테이블 CRUD 담당 리포지토리</summary>
    public class BookRepository
    {
        // ─── 조회 ──────────────────────────────────────────────────────────

        public List<Book> GetAll()
        {
            var list = new List<Book>();
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(
                "SELECT * FROM book ORDER BY book_id", conn);
            using var reader = cmd.ExecuteReader();

            while (reader.Read())
                list.Add(MapBook(reader));

            return list;
        }

        public List<Book> GetAvailable()
        {
            var list = new List<Book>();
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(
                "SELECT * FROM book WHERE is_available = 1 ORDER BY title", conn);
            using var reader = cmd.ExecuteReader();

            while (reader.Read())
                list.Add(MapBook(reader));

            return list;
        }

        public List<Book> SearchByTitle(string keyword)
        {
            var list = new List<Book>();
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(
                "SELECT * FROM book WHERE title LIKE @kw ORDER BY book_id", conn);
            cmd.Parameters.AddWithValue("@kw", $"%{keyword}%");
            using var reader = cmd.ExecuteReader();

            while (reader.Read())
                list.Add(MapBook(reader));

            return list;
        }

        // ─── 추가 ──────────────────────────────────────────────────────────

        public bool Add(Book book)
        {
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(
                @"INSERT INTO book (title, author, publisher, isbn)
                  VALUES (@title, @author, @publisher, @isbn)", conn);

            cmd.Parameters.AddWithValue("@title",     book.Title);
            cmd.Parameters.AddWithValue("@author",    book.Author);
            cmd.Parameters.AddWithValue("@publisher", book.Publisher);
            cmd.Parameters.AddWithValue("@isbn",      book.Isbn);

            return cmd.ExecuteNonQuery() > 0;
        }

        // ─── 삭제 ──────────────────────────────────────────────────────────

        /// <summary>
        /// 도서 삭제 — 현재 대출 중인 경우 삭제 불가 (false 반환)
        /// </summary>
        public bool Delete(int bookId)
        {
            using var conn = DatabaseManager.GetConnection();

            // 대출 중인지 확인
            using (var chk = new MySqlCommand(
                "SELECT COUNT(*) FROM borrow WHERE book_id=@id AND is_returned=0", conn))
            {
                chk.Parameters.AddWithValue("@id", bookId);
                if (Convert.ToInt64(chk.ExecuteScalar()) > 0)
                    return false;   // 대출중이므로 삭제 불가
            }

            using var cmd = new MySqlCommand(
                "DELETE FROM book WHERE book_id = @id", conn);
            cmd.Parameters.AddWithValue("@id", bookId);
            return cmd.ExecuteNonQuery() > 0;
        }

        // ─── 대출 가능 여부 업데이트 ────────────────────────────────────────

        public bool UpdateAvailability(int bookId, bool isAvailable)
        {
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(
                "UPDATE book SET is_available = @avail WHERE book_id = @id", conn);
            cmd.Parameters.AddWithValue("@avail", isAvailable ? 1 : 0);
            cmd.Parameters.AddWithValue("@id",    bookId);
            return cmd.ExecuteNonQuery() > 0;
        }

        // ─── 내부 헬퍼 ─────────────────────────────────────────────────────

        private static Book MapBook(MySqlDataReader r) => new Book
        {
            BookId      = r.GetInt32("book_id"),
            Title       = r.GetString("title"),
            Author      = r.IsDBNull(r.GetOrdinal("author"))    ? "" : r.GetString("author"),
            Publisher   = r.IsDBNull(r.GetOrdinal("publisher")) ? "" : r.GetString("publisher"),
            Isbn        = r.IsDBNull(r.GetOrdinal("isbn"))      ? "" : r.GetString("isbn"),
            IsAvailable = r.GetBoolean("is_available")
        };
    }
}
