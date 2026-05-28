using MySql.Data.MySqlClient;
using LibraryManagement.Database;
using LibraryManagement.Models;

namespace LibraryManagement.Repositories
{
    /// <summary>user 테이블 CRUD 담당 리포지토리</summary>
    public class UserRepository
    {
        // ─── 조회 ──────────────────────────────────────────────────────────

        public List<User> GetAll()
        {
            var list = new List<User>();
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(
                "SELECT * FROM user ORDER BY user_id", conn);
            using var reader = cmd.ExecuteReader();

            while (reader.Read())
                list.Add(MapUser(reader));

            return list;
        }

        public List<User> SearchByName(string keyword)
        {
            var list = new List<User>();
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(
                "SELECT * FROM user WHERE name LIKE @kw ORDER BY user_id", conn);
            cmd.Parameters.AddWithValue("@kw", $"%{keyword}%");
            using var reader = cmd.ExecuteReader();

            while (reader.Read())
                list.Add(MapUser(reader));

            return list;
        }

        // ─── 추가 ──────────────────────────────────────────────────────────

        public bool Add(User user)
        {
            using var conn = DatabaseManager.GetConnection();
            using var cmd  = new MySqlCommand(
                @"INSERT INTO user (name, phone, email)
                  VALUES (@name, @phone, @email)", conn);

            cmd.Parameters.AddWithValue("@name",  user.Name);
            cmd.Parameters.AddWithValue("@phone", user.Phone);
            cmd.Parameters.AddWithValue("@email", user.Email);

            return cmd.ExecuteNonQuery() > 0;
        }

        // ─── 삭제 ──────────────────────────────────────────────────────────

        /// <summary>
        /// 회원 삭제 — 현재 대출 중인 경우 삭제 불가 (false 반환)
        /// </summary>
        public bool Delete(int userId)
        {
            using var conn = DatabaseManager.GetConnection();

            // 대출 중인지 확인
            using (var chk = new MySqlCommand(
                "SELECT COUNT(*) FROM borrow WHERE user_id=@id AND is_returned=0", conn))
            {
                chk.Parameters.AddWithValue("@id", userId);
                if (Convert.ToInt64(chk.ExecuteScalar()) > 0)
                    return false;
            }

            using var cmd = new MySqlCommand(
                "DELETE FROM user WHERE user_id = @id", conn);
            cmd.Parameters.AddWithValue("@id", userId);
            return cmd.ExecuteNonQuery() > 0;
        }

        // ─── 내부 헬퍼 ─────────────────────────────────────────────────────

        private static User MapUser(MySqlDataReader r) => new User
        {
            UserId = r.GetInt32("user_id"),
            Name   = r.GetString("name"),
            Phone  = r.IsDBNull(r.GetOrdinal("phone")) ? "" : r.GetString("phone"),
            Email  = r.IsDBNull(r.GetOrdinal("email")) ? "" : r.GetString("email")
        };
    }
}
