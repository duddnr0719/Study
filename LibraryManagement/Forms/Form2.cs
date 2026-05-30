using System.Drawing;
using System.Windows.Forms;
using LibraryManagement.Models;

namespace LibraryManagement.Forms
{
    /// <summary>
    /// Form2 — 도서 추가 / 수정 / 삭제
    /// 교재 원본 컨트롤 이름 그대로 유지
    ///   textBox1: ISBN  textBox2: 도서명
    ///   textBox3: 출판사  textBox4: 페이지
    ///   button1: 추가  button2: 수정  button3: 삭제
    ///   dataGridView1: 도서 목록
    /// </summary>
    public class Form2 : Form
    {
        private TextBox      textBox1      = null!;
        private TextBox      textBox2      = null!;
        private TextBox      textBox3      = null!;
        private TextBox      textBox4      = null!;
        private Button       button1       = null!;
        private Button       button2       = null!;
        private Button       button3       = null!;
        private DataGridView dataGridView1 = null!;

        public Form2()
        {
            InitializeComponent();
            RefreshGrid();
        }

        // ════════════════════════════════════════════════════════════════
        //  UI 초기화
        // ════════════════════════════════════════════════════════════════
        private void InitializeComponent()
        {
            this.Text            = "도서 관리";
            this.Size            = new Size(780, 530);
            this.StartPosition   = FormStartPosition.CenterParent;
            this.BackColor       = Color.White;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox     = false;

            // ── 입력 패널 ─────────────────────────────────────────────────
            var pnlInput = new Panel
            {
                Dock      = DockStyle.Top,
                Height    = 175,
                BackColor = Color.FromArgb(236, 240, 241),
                Padding   = new Padding(15, 12, 15, 12)
            };

            // textBox1 – ISBN
            pnlInput.Controls.Add(MakeLabel("ISBN :", 12, 15));
            textBox1 = new TextBox { Location = new Point(80, 12), Width = 200 };

            // textBox2 – 도서명
            pnlInput.Controls.Add(MakeLabel("도서명 :", 12, 47));
            textBox2 = new TextBox { Location = new Point(80, 44), Width = 280 };

            // textBox3 – 출판사
            pnlInput.Controls.Add(MakeLabel("출판사 :", 12, 79));
            textBox3 = new TextBox { Location = new Point(80, 76), Width = 200 };

            // textBox4 – 페이지
            pnlInput.Controls.Add(MakeLabel("페이지 :", 12, 111));
            textBox4 = new TextBox { Location = new Point(80, 108), Width = 100 };

            // 버튼 3개
            button1 = MakeBtn("추가 (F1)", Color.FromArgb(52, 152, 219), new Point(400, 12));
            button2 = MakeBtn("수정 (F2)", Color.FromArgb(230, 126, 34), new Point(400, 52));
            button3 = MakeBtn("삭제 (F3)", Color.FromArgb(231, 76,  60), new Point(400, 92));

            button1.Click += Button1_Click;
            button2.Click += Button2_Click;
            button3.Click += Button3_Click;

            pnlInput.Controls.AddRange(new Control[]
                { textBox1, textBox2, textBox3, textBox4, button1, button2, button3 });

            // ── DataGridView ──────────────────────────────────────────────
            dataGridView1 = new DataGridView
            {
                Dock                  = DockStyle.Fill,
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
                    Font      = new Font("맑은 고딕", 9, FontStyle.Bold),
                    BackColor = Color.FromArgb(52, 73, 94),
                    ForeColor = Color.White,
                    SelectionBackColor = Color.FromArgb(52, 73, 94)
                }
            };
            dataGridView1.CellClick += DataGridView1_CellClick;

            this.Controls.AddRange(new Control[] { dataGridView1, pnlInput });

            // 단축키
            this.KeyPreview = true;
            this.KeyDown   += Form2_KeyDown;
        }

        // ════════════════════════════════════════════════════════════════
        //  그리드 새로고침 (메모리 리스트 → 화면)
        // ════════════════════════════════════════════════════════════════
        private void RefreshGrid()
        {
            dataGridView1.DataSource = DataManager.Books.Select(b => new
            {
                ISBN    = b.Isbn,
                도서명  = b.Name,
                출판사  = b.Publisher,
                페이지  = b.Page,
                상태    = b.isBorrowed ? "대출중" : "대출가능"
            }).ToList();
        }

        // ── 행 클릭 → 텍스트박스 자동 채우기 ────────────────────────────
        private void DataGridView1_CellClick(object? sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0) return;
            string isbn = dataGridView1.Rows[e.RowIndex].Cells["ISBN"].Value?.ToString() ?? "";
            var book = DataManager.Books.FirstOrDefault(b => b.Isbn == isbn);
            if (book == null) return;

            textBox1.Text = book.Isbn;
            textBox2.Text = book.Name;
            textBox3.Text = book.Publisher;
            textBox4.Text = book.Page.ToString();
        }

        // ════════════════════════════════════════════════════════════════
        //  추가 (button1) — 교재 원본 로직 그대로
        // ════════════════════════════════════════════════════════════════
        private void Button1_Click(object? sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(textBox1.Text) ||
                string.IsNullOrWhiteSpace(textBox2.Text))
            {
                MessageBox.Show("ISBN 과 도서명은 필수 입력입니다.",
                    "입력 오류", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // 중복 검사 (교재 원본: Books.Exists)
            if (DataManager.Books.Exists(x => x.Isbn == textBox1.Text.Trim()))
            {
                MessageBox.Show("이미 존재하는 도서입니다.",
                    "중복", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            var book = new Book
            {
                Isbn      = textBox1.Text.Trim(),
                Name      = textBox2.Text.Trim(),
                Publisher = textBox3.Text.Trim(),
                Page      = int.TryParse(textBox4.Text.Trim(), out int p) ? p : 0
            };

            DataManager.Books.Add(book);
            DataManager.Save();
            RefreshGrid();
            ClearInputs();
            MessageBox.Show("도서가 추가되었습니다.",
                "완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        // ════════════════════════════════════════════════════════════════
        //  수정 (button2) — 교재 원본 로직 그대로
        // ════════════════════════════════════════════════════════════════
        private void Button2_Click(object? sender, EventArgs e)
        {
            try
            {
                // Books.Single (교재 원본과 동일)
                var book = DataManager.Books.Single(
                    x => x.Isbn == textBox1.Text.Trim());

                book.Name      = textBox2.Text.Trim();
                book.Publisher = textBox3.Text.Trim();
                book.Page      = int.TryParse(textBox4.Text.Trim(), out int p) ? p : 0;

                DataManager.Save();
                RefreshGrid();
                ClearInputs();
                MessageBox.Show("도서 정보가 수정되었습니다.",
                    "완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch
            {
                MessageBox.Show("존재하지 않는 도서입니다.",
                    "오류", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ════════════════════════════════════════════════════════════════
        //  삭제 (button3) — 교재 원본 로직 그대로
        // ════════════════════════════════════════════════════════════════
        private void Button3_Click(object? sender, EventArgs e)
        {
            try
            {
                var book = DataManager.Books.Single(
                    x => x.Isbn == textBox1.Text.Trim());

                if (book.isBorrowed)
                {
                    MessageBox.Show("대여 중인 도서는 삭제할 수 없습니다.",
                        "삭제 불가", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                    return;
                }

                if (MessageBox.Show(
                        $"'{book.Name}' 도서를 삭제하시겠습니까?",
                        "삭제 확인",
                        MessageBoxButtons.YesNo, MessageBoxIcon.Question)
                    == DialogResult.Yes)
                {
                    DataManager.Books.Remove(book);
                    DataManager.Save();
                    RefreshGrid();
                    ClearInputs();
                }
            }
            catch
            {
                MessageBox.Show("존재하지 않는 도서입니다.",
                    "오류", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void Form2_KeyDown(object? sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.F1) Button1_Click(null, EventArgs.Empty);
            if (e.KeyCode == Keys.F2) Button2_Click(null, EventArgs.Empty);
            if (e.KeyCode == Keys.F3) Button3_Click(null, EventArgs.Empty);
        }

        private void ClearInputs()
        {
            textBox1.Clear(); textBox2.Clear();
            textBox3.Clear(); textBox4.Clear();
        }

        private static Label MakeLabel(string text, int x, int y) => new Label
        {
            Text     = text, Location = new Point(x, y),
            AutoSize = true, Font     = new Font("맑은 고딕", 9)
        };

        private static Button MakeBtn(string text, Color back, Point loc) => new Button
        {
            Text      = text, Location  = loc, Width = 120, Height = 32,
            BackColor = back, ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat,
            Font      = new Font("맑은 고딕", 9), Cursor = Cursors.Hand
        };
    }
}
