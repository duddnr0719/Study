using System.Drawing;
using System.Windows.Forms;
using LibraryManagement.Models;

namespace LibraryManagement.Forms
{
    /// <summary>
    /// Form1 — 메인 화면
    /// - MenuStrip: 도서관리(Form2), 사용자관리(Form3)
    /// - 통계 레이블: 전체도서(label5), 사용자수(label6), 대출중(label17), 연체중(label18)
    /// - dataGridView1: 도서 현황 / dataGridView2: 사용자 현황
    /// - 대출(button1) / 반납(button2)
    /// </summary>
    public class Form1 : Form
    {
        // ── MenuStrip ────────────────────────────────────────────────────
        private MenuStrip        menuStrip1         = null!;
        private ToolStripMenuItem toolStripMenuItem1 = null!;  // 도서관리
        private ToolStripMenuItem toolStripMenuItem2 = null!;  // 사용자관리

        // ── 통계 레이블 (교재 원본과 동일한 이름) ────────────────────────
        private Label label5  = null!;   // 전체 도서수
        private Label label6  = null!;   // 사용자수
        private Label label17 = null!;   // 대출중
        private Label label18 = null!;   // 연체중

        // ── DataGridViews ─────────────────────────────────────────────────
        private DataGridView dataGridView1 = null!;  // 도서 현황
        private DataGridView dataGridView2 = null!;  // 사용자 현황

        // ── 입력 컨트롤 ───────────────────────────────────────────────────
        private TextBox textBox1 = null!;  // ISBN
        private TextBox textBox2 = null!;  // 도서명 (ISBN 입력 시 자동 표시)
        private TextBox textBox3 = null!;  // 사용자 ID

        // ── 버튼 ──────────────────────────────────────────────────────────
        private Button button1 = null!;  // 대여
        private Button button2 = null!;  // 반납

        public Form1()
        {
            InitializeComponent();
            RefreshDisplay();
        }

        // ════════════════════════════════════════════════════════════════
        //  UI 초기화
        // ════════════════════════════════════════════════════════════════
        private void InitializeComponent()
        {
            this.Text            = "도서관리 프로그램";
            this.Size            = new Size(960, 680);
            this.MinimumSize     = new Size(960, 680);
            this.StartPosition   = FormStartPosition.CenterScreen;
            this.BackColor       = Color.White;

            // ── MenuStrip ────────────────────────────────────────────────
            menuStrip1        = new MenuStrip { BackColor = Color.FromArgb(44, 62, 80) };
            toolStripMenuItem1 = new ToolStripMenuItem("도서 관리")
                { ForeColor = Color.White, Font = new Font("맑은 고딕", 10) };
            toolStripMenuItem2 = new ToolStripMenuItem("사용자 관리")
                { ForeColor = Color.White, Font = new Font("맑은 고딕", 10) };

            toolStripMenuItem1.Click += (_, _) => { new Form2().ShowDialog(this); RefreshDisplay(); };
            toolStripMenuItem2.Click += (_, _) => { new Form3().ShowDialog(this); RefreshDisplay(); };

            menuStrip1.Items.AddRange(new ToolStripItem[]
                { toolStripMenuItem1, toolStripMenuItem2 });
            this.MainMenuStrip = menuStrip1;
            this.Controls.Add(menuStrip1);

            // ── 통계 패널 ─────────────────────────────────────────────────
            var pnlStats = new Panel
            {
                Dock      = DockStyle.Top,
                Height    = 52,
                BackColor = Color.FromArgb(236, 240, 241)
            };

            // 정적 텍스트 + 동적 값 쌍 x 4
            int sx = 12;
            pnlStats.Controls.Add(MakeStaticLabel("전체 도서수 :", sx, 14));
            label5 = MakeDynLabel("0", sx + 90, 14, Color.FromArgb(41, 128, 185));
            pnlStats.Controls.Add(label5);

            pnlStats.Controls.Add(MakeStaticLabel("사용자수 :", sx + 170, 14));
            label6 = MakeDynLabel("0", sx + 250, 14, Color.FromArgb(39, 174, 96));
            pnlStats.Controls.Add(label6);

            pnlStats.Controls.Add(MakeStaticLabel("대출 중 :", sx + 330, 14));
            label17 = MakeDynLabel("0", sx + 400, 14, Color.FromArgb(230, 126, 34));
            pnlStats.Controls.Add(label17);

            pnlStats.Controls.Add(MakeStaticLabel("연체 중 :", sx + 490, 14));
            label18 = MakeDynLabel("0", sx + 560, 14, Color.FromArgb(192, 57, 43));
            pnlStats.Controls.Add(label18);

            // ── 입력 / 버튼 패널 (하단) ───────────────────────────────────
            var pnlInput = new Panel
            {
                Dock      = DockStyle.Bottom,
                Height    = 125,
                BackColor = Color.FromArgb(236, 240, 241),
                Padding   = new Padding(12, 10, 12, 10)
            };

            // Row 1
            pnlInput.Controls.Add(MakeLabel("ISBN :", 12, 14));
            textBox1 = new TextBox { Location = new Point(70, 11), Width = 160 };
            textBox1.TextChanged += TextBox1_TextChanged;

            pnlInput.Controls.Add(MakeLabel("도서명 :", 245, 14));
            textBox2 = new TextBox
            {
                Location  = new Point(318, 11), Width = 280,
                BackColor = Color.FromArgb(220, 220, 220),
                ReadOnly  = true            // ISBN 입력 시 자동 채워짐
            };

            // Row 2
            pnlInput.Controls.Add(MakeLabel("사용자 ID :", 12, 52));
            textBox3 = new TextBox { Location = new Point(90, 49), Width = 120 };

            button1 = MakeBtn("대여 (F5)",    Color.FromArgb(52, 152, 219), new Point(12,  87));
            button2 = MakeBtn("반납 (F6)",    Color.FromArgb(39, 174, 96),  new Point(132, 87));

            button1.Click += Button1_Click;
            button2.Click += Button2_Click;

            pnlInput.Controls.AddRange(new Control[]
                { textBox1, textBox2, textBox3, button1, button2 });

            // ── 그리드 영역 ───────────────────────────────────────────────
            var pnlGrids = new Panel { Dock = DockStyle.Fill };

            // 도서 현황 제목
            var lblGrid1 = new Label
            {
                Text      = "도서 현황",
                Dock      = DockStyle.None,
                Font      = new Font("맑은 고딕", 9, FontStyle.Bold),
                ForeColor = Color.FromArgb(44, 62, 80),
                AutoSize  = true
            };

            dataGridView1 = MakeGrid();
            dataGridView2 = MakeGrid();

            pnlGrids.Controls.AddRange(new Control[] { dataGridView1, dataGridView2 });
            pnlGrids.Resize += (_, _) => LayoutGrids(pnlGrids);

            // ── 전체 조립 ─────────────────────────────────────────────────
            this.Controls.AddRange(new Control[] { pnlGrids, pnlStats, pnlInput });

            // 단축키
            this.KeyPreview = true;
            this.KeyDown   += Form1_KeyDown;
        }

        // ════════════════════════════════════════════════════════════════
        //  그리드 레이아웃 (좌 60% 도서 / 우 40% 사용자)
        // ════════════════════════════════════════════════════════════════
        private void LayoutGrids(Panel p)
        {
            int w = p.Width;
            int h = p.Height;
            int split = (int)(w * 0.62);

            dataGridView1.Location = new Point(0, 0);
            dataGridView1.Size     = new Size(split - 1, h);

            dataGridView2.Location = new Point(split + 1, 0);
            dataGridView2.Size     = new Size(w - split - 1, h);
        }

        // ════════════════════════════════════════════════════════════════
        //  데이터 새로고침 (교재 원본의 Form1_Load 역할)
        // ════════════════════════════════════════════════════════════════
        private void RefreshDisplay()
        {
            DataManager.Load();

            // 통계 — 교재 원본 코드와 동일한 로직
            label5.Text  = DataManager.Books.Count.ToString();
            label6.Text  = DataManager.Users.Count.ToString();
            label17.Text = DataManager.Books.Count(x => x.isBorrowed).ToString();
            label18.Text = DataManager.Books
                .Count(x => x.isBorrowed && x.BorrowedAt.AddDays(7) < DateTime.Now)
                .ToString();

            // 도서 현황 그리드
            dataGridView1.DataSource = DataManager.Books.Select(b => new
            {
                ISBN    = b.Isbn,
                도서명  = b.Name,
                출판사  = b.Publisher,
                페이지  = b.Page,
                상태    = b.isBorrowed ? "대출중" : "대출가능",
                대출자  = b.UserName,
                대출일  = b.isBorrowed ? b.BorrowedAt.ToString("yyyy-MM-dd") : "",
                연체    = (b.isBorrowed && b.BorrowedAt.AddDays(7) < DateTime.Now)
                             ? "⚠ 연체" : ""
            }).ToList();

            // 사용자 현황 그리드
            dataGridView2.DataSource = DataManager.Users.Select(u => new
            {
                ID   = u.Id,
                이름 = u.Name
            }).ToList();

            // 입력 필드 초기화
            textBox1.Clear();
            textBox2.Clear();
            textBox3.Clear();
        }

        // ════════════════════════════════════════════════════════════════
        //  ISBN 입력 → 도서명 자동 표시
        // ════════════════════════════════════════════════════════════════
        private void TextBox1_TextChanged(object? sender, EventArgs e)
        {
            var book = DataManager.Books
                .FirstOrDefault(b => b.Isbn == textBox1.Text.Trim());
            textBox2.Text = book?.Name ?? "";
        }

        // ════════════════════════════════════════════════════════════════
        //  대여 처리 (button1) — 교재 원본 로직 그대로
        // ════════════════════════════════════════════════════════════════
        private void Button1_Click(object? sender, EventArgs e)
        {
            try
            {
                // ISBN 으로 도서 검색
                var book = DataManager.Books.Single(
                    x => x.Isbn == textBox1.Text.Trim());

                if (book.isBorrowed)
                {
                    MessageBox.Show("이미 대여 중인 도서입니다.",
                        "대여 불가", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                // 사용자 ID 로 사용자 검색
                var user = DataManager.Users.Single(
                    x => x.Id == int.Parse(textBox3.Text.Trim()));

                // 대출 정보 업데이트 (교재 원본과 동일)
                book.UserId     = user.Id;
                book.UserName   = user.Name;
                book.isBorrowed = true;
                book.BorrowedAt = DateTime.Now;

                DataManager.Save();                              // book 테이블 갱신
                DataManager.LogBorrow(book.Isbn, user.Id, book.BorrowedAt);  // borrow 이력

                RefreshDisplay();
                MessageBox.Show(
                    $"'{book.Name}' 도서를 '{user.Name}'님에게 대여했습니다.\n" +
                    $"반납 기한: {book.BorrowedAt.AddDays(7):yyyy-MM-dd}",
                    "대여 완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch (InvalidOperationException)
            {
                MessageBox.Show("존재하지 않는 도서 또는 사용자입니다.",
                    "오류", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
            catch (FormatException)
            {
                MessageBox.Show("사용자 ID 는 숫자로 입력하세요.",
                    "입력 오류", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        // ════════════════════════════════════════════════════════════════
        //  반납 처리 (button2) — 교재 원본 로직 그대로 (7일 연체 체크)
        // ════════════════════════════════════════════════════════════════
        private void Button2_Click(object? sender, EventArgs e)
        {
            try
            {
                var book = DataManager.Books.Single(
                    x => x.Isbn == textBox1.Text.Trim());

                if (!book.isBorrowed)
                {
                    MessageBox.Show("대여 상태가 아닙니다.",
                        "반납 불가", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                // 연체 확인 (7일 기준 — 교재 원본과 동일)
                if (book.BorrowedAt.AddDays(7) < DateTime.Now)
                {
                    int overdueDays = (int)(DateTime.Now - book.BorrowedAt.AddDays(7)).TotalDays;
                    MessageBox.Show(
                        $"연체 상태로 반납되었습니다.\n" +
                        $"대여일: {book.BorrowedAt:yyyy-MM-dd}\n" +
                        $"연체 일수: {overdueDays}일",
                        "연체 반납", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                }
                else
                {
                    MessageBox.Show(
                        $"정상 반납되었습니다.\n도서명: {book.Name}",
                        "반납 완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
                }

                DataManager.LogReturn(book.Isbn);   // borrow 이력 갱신

                // 도서 대출 정보 초기화 (교재 원본과 동일)
                book.UserId     = 0;
                book.UserName   = "";
                book.isBorrowed = false;
                book.BorrowedAt = new DateTime();

                DataManager.Save();
                RefreshDisplay();
            }
            catch (InvalidOperationException)
            {
                MessageBox.Show("존재하지 않는 도서입니다.",
                    "오류", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ── 단축키 F5 / F6 ───────────────────────────────────────────────
        private void Form1_KeyDown(object? sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.F5) Button1_Click(null, EventArgs.Empty);
            if (e.KeyCode == Keys.F6) Button2_Click(null, EventArgs.Empty);
        }

        // ════════════════════════════════════════════════════════════════
        //  헬퍼 메서드
        // ════════════════════════════════════════════════════════════════
        private static DataGridView MakeGrid() => new DataGridView
        {
            ReadOnly              = true,
            AllowUserToAddRows    = false,
            AllowUserToDeleteRows = false,
            SelectionMode         = DataGridViewSelectionMode.FullRowSelect,
            MultiSelect           = false,
            AutoSizeColumnsMode   = DataGridViewAutoSizeColumnsMode.Fill,
            BackgroundColor       = Color.White,
            BorderStyle           = BorderStyle.None,
            RowHeadersVisible     = false,
            Font                  = new Font("맑은 고딕", 9),
            ColumnHeadersDefaultCellStyle =
            {
                Font            = new Font("맑은 고딕", 9, FontStyle.Bold),
                BackColor       = Color.FromArgb(52, 73, 94),
                ForeColor       = Color.White,
                SelectionBackColor = Color.FromArgb(52, 73, 94)
            }
        };

        private static Label MakeStaticLabel(string text, int x, int y) => new Label
        {
            Text      = text,
            Location  = new Point(x, y),
            AutoSize  = true,
            Font      = new Font("맑은 고딕", 9),
            ForeColor = Color.FromArgb(52, 73, 94)
        };

        private static Label MakeDynLabel(string text, int x, int y, Color color) => new Label
        {
            Text      = text,
            Location  = new Point(x, y),
            AutoSize  = true,
            Font      = new Font("맑은 고딕", 11, FontStyle.Bold),
            ForeColor = color
        };

        private static Label MakeLabel(string text, int x, int y) => new Label
        {
            Text      = text,
            Location  = new Point(x, y),
            AutoSize  = true,
            Font      = new Font("맑은 고딕", 9),
            ForeColor = Color.FromArgb(52, 73, 94)
        };

        private static Button MakeBtn(string text, Color back, Point loc) => new Button
        {
            Text      = text,
            Location  = loc,
            Width     = 110,
            Height    = 30,
            BackColor = back,
            ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat,
            Font      = new Font("맑은 고딕", 9, FontStyle.Bold),
            Cursor    = Cursors.Hand
        };
    }
}
