using System.Drawing;
using System.Windows.Forms;
using LibraryManagement.Models;

namespace LibraryManagement.Forms
{
    /// <summary>
    /// Form3 — 사용자 추가 / 수정 / 삭제
    /// 교재 원본 컨트롤 이름 그대로 유지
    ///   textBox1: 사용자 ID  textBox2: 이름
    ///   button1: 추가  button2: 수정  button3: 삭제
    ///   dataGridView1: 사용자 목록
    /// </summary>
    public class Form3 : Form
    {
        private TextBox      textBox1      = null!;
        private TextBox      textBox2      = null!;
        private Button       button1       = null!;
        private Button       button2       = null!;
        private Button       button3       = null!;
        private DataGridView dataGridView1 = null!;

        public Form3()
        {
            InitializeComponent();
            RefreshGrid();
        }

        // ════════════════════════════════════════════════════════════════
        //  UI 초기화
        // ════════════════════════════════════════════════════════════════
        private void InitializeComponent()
        {
            this.Text            = "사용자 관리";
            this.Size            = new Size(580, 480);
            this.StartPosition   = FormStartPosition.CenterParent;
            this.BackColor       = Color.White;
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox     = false;

            // ── 입력 패널 ─────────────────────────────────────────────────
            var pnlInput = new Panel
            {
                Dock      = DockStyle.Top,
                Height    = 120,
                BackColor = Color.FromArgb(236, 240, 241),
                Padding   = new Padding(15, 12, 15, 12)
            };

            // textBox1 – 사용자 ID
            pnlInput.Controls.Add(MakeLabel("사용자 ID :", 12, 15));
            textBox1 = new TextBox { Location = new Point(95, 12), Width = 130 };

            // textBox2 – 이름
            pnlInput.Controls.Add(MakeLabel("이름 :", 12, 50));
            textBox2 = new TextBox { Location = new Point(95, 47), Width = 200 };

            // 버튼 3개
            button1 = MakeBtn("추가 (F1)", Color.FromArgb(52, 152, 219), new Point(320, 12));
            button2 = MakeBtn("수정 (F2)", Color.FromArgb(230, 126, 34), new Point(320, 52));
            button3 = MakeBtn("삭제 (F3)", Color.FromArgb(231, 76,  60), new Point(320, 78));

            button1.Click += Button1_Click;
            button2.Click += Button2_Click;
            button3.Click += Button3_Click;

            pnlInput.Controls.AddRange(new Control[]
                { textBox1, textBox2, button1, button2, button3 });

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
            this.KeyDown   += Form3_KeyDown;
        }

        // ════════════════════════════════════════════════════════════════
        //  그리드 새로고침
        // ════════════════════════════════════════════════════════════════
        private void RefreshGrid()
        {
            dataGridView1.DataSource = DataManager.Users.Select(u => new
            {
                ID   = u.Id,
                이름 = u.Name
            }).ToList();
        }

        // ── 행 클릭 → 텍스트박스 자동 채우기 ────────────────────────────
        private void DataGridView1_CellClick(object? sender, DataGridViewCellEventArgs e)
        {
            if (e.RowIndex < 0) return;
            var idVal = dataGridView1.Rows[e.RowIndex].Cells["ID"].Value;
            if (idVal == null) return;

            int id = Convert.ToInt32(idVal);
            var user = DataManager.Users.FirstOrDefault(u => u.Id == id);
            if (user == null) return;

            textBox1.Text = user.Id.ToString();
            textBox2.Text = user.Name;
        }

        // ════════════════════════════════════════════════════════════════
        //  추가 (button1) — 교재 원본 로직 그대로
        // ════════════════════════════════════════════════════════════════
        private void Button1_Click(object? sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(textBox1.Text) ||
                string.IsNullOrWhiteSpace(textBox2.Text))
            {
                MessageBox.Show("사용자 ID 와 이름은 필수 입력입니다.",
                    "입력 오류", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            if (!int.TryParse(textBox1.Text.Trim(), out int id))
            {
                MessageBox.Show("사용자 ID 는 숫자로 입력하세요.",
                    "입력 오류", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            // 중복 검사 (교재 원본: Users.Exists)
            if (DataManager.Users.Exists(x => x.Id == id))
            {
                MessageBox.Show("사용자 ID 가 겹칩니다.",
                    "중복", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            DataManager.Users.Add(new User { Id = id, Name = textBox2.Text.Trim() });
            DataManager.Save();
            RefreshGrid();
            ClearInputs();
            MessageBox.Show("사용자가 추가되었습니다.",
                "완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }

        // ════════════════════════════════════════════════════════════════
        //  수정 (button2) — 교재 원본 로직 그대로
        // ════════════════════════════════════════════════════════════════
        private void Button2_Click(object? sender, EventArgs e)
        {
            try
            {
                int id   = int.Parse(textBox1.Text.Trim());
                var user = DataManager.Users.Single(x => x.Id == id);

                user.Name = textBox2.Text.Trim();

                DataManager.Save();
                RefreshGrid();
                ClearInputs();
                MessageBox.Show("사용자 정보가 수정되었습니다.",
                    "완료", MessageBoxButtons.OK, MessageBoxIcon.Information);
            }
            catch
            {
                MessageBox.Show("존재하지 않는 사용자입니다.",
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
                int id   = int.Parse(textBox1.Text.Trim());
                var user = DataManager.Users.Single(x => x.Id == id);

                if (MessageBox.Show(
                        $"'{user.Name}' 사용자를 삭제하시겠습니까?",
                        "삭제 확인",
                        MessageBoxButtons.YesNo, MessageBoxIcon.Question)
                    == DialogResult.Yes)
                {
                    DataManager.Users.Remove(user);
                    DataManager.Save();
                    RefreshGrid();
                    ClearInputs();
                }
            }
            catch
            {
                MessageBox.Show("존재하지 않는 사용자입니다.",
                    "오류", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private void Form3_KeyDown(object? sender, KeyEventArgs e)
        {
            if (e.KeyCode == Keys.F1) Button1_Click(null, EventArgs.Empty);
            if (e.KeyCode == Keys.F2) Button2_Click(null, EventArgs.Empty);
            if (e.KeyCode == Keys.F3) Button3_Click(null, EventArgs.Empty);
        }

        private void ClearInputs() { textBox1.Clear(); textBox2.Clear(); }

        private static Label MakeLabel(string text, int x, int y) => new Label
        {
            Text     = text, Location = new Point(x, y),
            AutoSize = true, Font     = new Font("맑은 고딕", 9)
        };

        private static Button MakeBtn(string text, Color back, Point loc) => new Button
        {
            Text      = text, Location  = loc, Width = 120, Height = 30,
            BackColor = back, ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat,
            Font      = new Font("맑은 고딕", 9), Cursor = Cursors.Hand
        };
    }
}
