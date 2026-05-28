using System.Drawing;
using System.Windows.Forms;

namespace LibraryManagement.Forms
{
    /// <summary>메인 화면 — 도서관리 시스템 진입점</summary>
    public class MainForm : Form
    {
        private Button btnBook   = null!;
        private Button btnUser   = null!;
        private Button btnBorrow = null!;
        private Label  lblStatus = null!;

        public MainForm()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Text            = "도서관리 시스템";
            this.Size            = new Size(480, 420);
            this.MinimumSize     = new Size(480, 420);
            this.StartPosition   = FormStartPosition.CenterScreen;
            this.BackColor       = Color.WhiteSmoke;
            this.FormBorderStyle = FormBorderStyle.FixedSingle;
            this.MaximizeBox     = false;

            // ── 헤더 패널 ──────────────────────────────────────────────────
            var pnlHeader = new Panel
            {
                Dock      = DockStyle.Top,
                Height    = 100,
                BackColor = Color.FromArgb(41, 128, 185)
            };

            var lblTitle = new Label
            {
                Text      = "📚  도서관리 시스템",
                Font      = new Font("맑은 고딕", 20, FontStyle.Bold),
                ForeColor = Color.White,
                AutoSize  = false,
                TextAlign = ContentAlignment.MiddleCenter,
                Dock      = DockStyle.Fill
            };
            pnlHeader.Controls.Add(lblTitle);

            // ── 중앙 버튼 패널 ─────────────────────────────────────────────
            var pnlCenter = new Panel
            {
                Dock      = DockStyle.Fill,
                BackColor = Color.WhiteSmoke,
                Padding   = new Padding(60, 30, 60, 10)
            };

            btnBook = MakeMenuButton("📖  도서 관리", Color.FromArgb(52, 152, 219));
            btnUser = MakeMenuButton("👤  회원 관리", Color.FromArgb(46, 204, 113));
            btnBorrow = MakeMenuButton("📋  대출 / 반납 관리", Color.FromArgb(155, 89, 182));

            btnBook.Location   = new Point(60, 30);
            btnBook.Width      = 320;
            btnUser.Location   = new Point(60, 100);
            btnUser.Width      = 320;
            btnBorrow.Location = new Point(60, 170);
            btnBorrow.Width    = 320;

            btnBook.Click   += (_, _) => new BookForm().ShowDialog(this);
            btnUser.Click   += (_, _) => new UserForm().ShowDialog(this);
            btnBorrow.Click += (_, _) => new BorrowForm().ShowDialog(this);

            pnlCenter.Controls.AddRange(new Control[] { btnBook, btnUser, btnBorrow });

            // ── 상태 바 ────────────────────────────────────────────────────
            var pnlStatus = new Panel
            {
                Dock      = DockStyle.Bottom,
                Height    = 30,
                BackColor = Color.FromArgb(189, 195, 199)
            };

            lblStatus = new Label
            {
                Text      = "✅  MySQL 연결됨  |  DB: sch  |  root@localhost",
                Font      = new Font("맑은 고딕", 9),
                ForeColor = Color.FromArgb(44, 62, 80),
                AutoSize  = false,
                TextAlign = ContentAlignment.MiddleCenter,
                Dock      = DockStyle.Fill
            };
            pnlStatus.Controls.Add(lblStatus);

            this.Controls.AddRange(new Control[] { pnlCenter, pnlHeader, pnlStatus });
        }

        private static Button MakeMenuButton(string text, Color backColor)
        {
            return new Button
            {
                Text      = text,
                Height    = 55,
                Font      = new Font("맑은 고딕", 14, FontStyle.Bold),
                BackColor = backColor,
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat,
                Cursor    = Cursors.Hand
            };
        }
    }
}
