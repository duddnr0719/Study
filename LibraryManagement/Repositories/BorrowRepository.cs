using MySql.Data.MySqlClient;
using LibraryManagement.Database;
using LibraryManagement.Models;

namespace LibraryManagement.Repositories
{
    /// <summary>borrow 테이블 CRUD 및 대출/반납 처리 리포지토리</summary>
    public class BorrowRepository
    {
        // ─── 조회 ──────────────────────────────────────────────────────────

        /// <summary>전체 대출 목록 (book, user JOIN)</summary>
        public List<Borrow> GetAll()
        {
            var list = new List<Borrow>();
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(@"
                SELECT b.borrow_id,  b.book_id,    b.user_id,
                       bk.title  AS book_title,
                       u.name    AS user_name,
                       b.borrow_date, b.return_date, b.is_returned
                FROM   borrow b
                JOIN   book bk ON b.book_id  = bk.book_id
                JOIN   user u  ON b.user_id  = u.user_id
                ORDER  BY b.borrow_id DESC", conn);
            using var reader = cmd.ExecuteReader();

            while (reader.Read())
                list.Add(MapBorrow(reader));

            return list;
        }

        /// <summary>현재 대출 중(미반납) 목록</summary>
        public List<Borrow> GetActive()
        {
            var list = new List<Borrow>();
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(@"
                SELECT b.borrow_id,  b.book_id,    b.user_id,
                       bk.title  AS book_title,
                       u.name    AS user_name,
                       b.borrow_date, b.return_date, b.is_returned
                FROM   borrow b
                JOIN   book bk ON b.book_id  = bk.book_id
                JOIN   user u  ON b.user_id  = u.user_id
                WHERE  b.is_returned = 0
                ORDER  BY b.borrow_date", conn);
            using var reader = cmd.ExecuteReader();

            while (reader.Read())
                list.Add(MapBorrow(reader));

            return list;
        }

        // ─── 대출 등록 ─────────────────────────────────────────────────────

        /// <summary>
        /// 대출 등록 — borrow 행 추가 + book.is_available = 0
        /// </summary>
        public bool Add(Borrow borrow)
        {
            using var conn = DatabaseManager.GetConnection();
            using var tx   = conn.BeginTransaction();

            try
            {
                // borrow 행 삽입
                using (var cmd = new MySqlCommand(@"
                    INSERT INTO borrow (book_id, user_id, borrow_date, return_date)
                    VALUES (@bid, @uid, @bdate, @rdate)", conn, tx))
                {
                    cmd.Parameters.AddWithValue("@bid",   borrow.BookId);
                    cmd.Parameters.AddWithValue("@uid",   borrow.UserId);
                    cmd.Parameters.AddWithValue("@bdate", borrow.BorrowDate.ToString("yyyy-MM-dd"));
                    cmd.Parameters.AddWithValue("@rdate",
                        borrow.ReturnDate.HasValue
                            ? (object)borrow.ReturnDate.Value.ToString("yyyy-MM-dd")
                            : DBNull.Value);
                    cmd.ExecuteNonQuery();
                }

                // 도서 대출 불가 상태로 변경
                using (var cmd = new MySqlCommand(
                    "UPDATE book SET is_available = 0 WHERE book_id = @bid", conn, tx))
                {
                    cmd.Parameters.AddWithValue("@bid", borrow.BookId);
                    cmd.ExecuteNonQuery();
                }

                tx.Commit();
                return true;
            }
            catch
            {
                tx.Rollback();
                throw;
            }
        }

        // ─── 반납 처리 ─────────────────────────────────────────────────────

        /// <summary>
        /// 반납 처리 — borrow.is_returned = 1 + book.is_available = 1
        /// </summary>
        public bool Return(int borrowId)
        {
            using var conn = DatabaseManager.GetConnection();

            // book_id 조회
            int bookId;
            using (var sel = new MySqlCommand(
                "SELECT book_id FROM borrow WHERE borrow_id = @id", conn))
            {
                sel.Parameters.AddWithValue("@id", borrowId);
                var result = sel.ExecuteScalar();
                if (result == null) return false;
                bookId = Convert.ToInt32(result);
            }

            using var tx = conn.BeginTransaction();
            try
            {
                // 반납 처리
                using (var cmd = new MySqlCommand(@"
                    UPDATE borrow
                    SET    is_returned = 1
                    WHERE  borrow_id  = @id", conn, tx))
                {
                    cmd.Parameters.AddWithValue("@id", borrowId);
                    cmd.ExecuteNonQuery();
                }

                // 도서 대출 가능 상태로 변경
                using (var cmd = new MySqlCommand(
                    "UPDATE book SET is_available = 1 WHERE book_id = @bid", conn, tx))
                {
                    cmd.Parameters.AddWithValue("@bid", bookId);
                    cmd.ExecuteNonQuery();
                }

                tx.Commit();
                return true;
            }
            catch
            {
                tx.Rollback();
                throw;
            }
        }

        // ─── 내부 헬퍼 ─────────────────────────────────────────────────────

        private static Borrow MapBorrow(MySqlDataReader r) => new Borrow
        {
            BorrowId   = r.GetInt32("borrow_id"),
            BookId     = r.GetInt32("book_id"),
            UserId     = r.GetInt32("user_id"),
            BookTitle  = r.IsDBNull(r.GetOrdinal("book_title")) ? "" : r.GetString("book_title"),
            UserName   = r.IsDBNull(r.GetOrdinal("user_name"))  ? "" : r.GetString("user_name"),
            BorrowDate = r.GetDateTime("borrow_date"),
            ReturnDate = r.IsDBNull(r.GetOrdinal("return_date"))
                         ? null : r.GetDateTime("return_date"),
            IsReturned = r.GetBoolean("is_returned")
        };
    }
}
