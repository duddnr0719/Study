using System.Windows.Forms;
using LibraryManagement.Database;
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

            try
            {
                // 프로그램 시작 시 DB / 테이블 자동 생성
                DatabaseManager.InitializeDatabase();
            }
            catch (Exception ex)
            {
                MessageBox.Show(
                    $"MySQL 데이터베이스 연결에 실패했습니다.\n\n" +
                    $"접속 정보: root@localhost / 1111 / DB: sch\n\n" +
                    $"오류 내용:\n{ex.Message}",
                    "데이터베이스 연결 오류",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
                return;
            }

            Application.Run(new MainForm());
        }
    }
}
