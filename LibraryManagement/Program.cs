using System.Windows.Forms;
using LibraryManagement.Forms;

namespace LibraryManagement
{
    internal static class Program
    {
        [STAThread]
        static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            // MySQL DB / 테이블 자동 생성
            try
            {
                DatabaseManager.InitializeDatabase();
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    "MySQL 데이터베이스에 연결할 수 없습니다.\n\n" +
                    "확인 사항:\n" +
                    "  · MySQL 서버가 실행 중인지 확인하세요.\n" +
                    "  · 접속 정보: root / 1111 / localhost\n\n" +
                    $"오류 내용:\n{ex.Message}",
                    "DB 연결 오류",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return;
            }

            Application.Run(new Form1());
        }
    }
}
