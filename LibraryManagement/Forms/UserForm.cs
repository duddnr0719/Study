using System.Drawing;
using System.Windows.Forms;
using LibraryManagement.Repositories;

namespace LibraryManagement.Forms
{
    /// <summary>회원 관리 폼 — user 테이블 조회/추가/삭제</summary>
    public class UserForm : Form
    {
        private DataGridView dgv       = null!;
        private TextBox      txtSearch = null!;
        private Button       btnSearch = null!;
        private Button       btnAll    = null!;
        private Button       btnAdd    = null!;
        private Button       btnDelete = null!;
        private Label        lblCount  = null!;

        private readonly UserRepository repo = new();

        public UserForm()
        {
            InitializeComponent();
            LoadAll();
        }

        private void InitializeComponent()
        {
            this.Text          = "회원 관리";
            this.Size          = new Size(720, 520);
            this.StartPosition = FormStartPosition.CenterParent;
            this.BackColor     = Color.White;

            // ── 검색 패널 ─────────────────────────────────────────────────
            var pnlTop = new Panel
            {
                Dock      = DockStyle.Top,
                Height    = 50,
                BackColor = Color.FromArgb(236, 240, 241),
                Padding   = new Padding(10, 8, 10, 8)
            };

            var lblSearch = new Label
            {
                Text     = "이름 검색:",
                Location = new Point(10, 12),
                AutoSize = true,
                Font     = new Font("맑은 고딕", 9)
            };

            txtSearch = new TextBox
            {
                Location = new Point(80, 9),
                Width    = 250,
                Height   = 25
            };
            txtSearch.KeyDown += (_, e) =>
            {
                if (e.KeyCode == Keys.Enter) BtnSearch_Click(null, EventArgs.Empty);
            };

            btnSearch = MakeButton("🔍 검색",  Color.FromArgb(46, 204, 113));
            btnAll    = MakeButton("전체 목록", Color.FromArgb(149, 165, 166));

            btnSearch.Location = new Point(340, 8);
            btnSearch.Width    = 80;
            btnAll.Location    = new Point(430, 8);
            btnAll.Width       = 80;

            btnSearch.Click += BtnSearch_Click;
            btnAll.Click    += (_, _) => LoadAll();

            pnlTop.Controls.AddRange(new Control[]
                { lblSearch, txtSearch, btnSearch, btnAll });

            // ── DataGridView ──────────────────────────────────────────────
            dgv = new DataGridView
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
                Font                  = new Font("맑은 고딕", 9)
            };
            dgv.ColumnHeadersDefaultCellStyle.Font =
                new Font("맑은 고딕", 9, FontStyle.Bold);

            // ── 하단 버튼 패널 ────────────────────────────────────────────
            var pnlBottom = new Panel
            {
                Dock      = DockStyle.Bottom,
                Height    = 50,
                BackColor = Color.FromArgb(236, 240, 241),
                Padding   = new Padding(10, 8, 10, 8)
            };

            btnAdd    = MakeButton("➕ 회원 추가",  Color.FromArgb(46, 204, 113));
            btnDelete = MakeButton("🗑️ 선택 삭제", Color.FromArgb(231, 76, 60));
            lblCount  = new Label
            {
                AutoSize  = true,
                ForeColor = Color.FromArgb(52, 73, 94),
                Font      = new Font("맑은 고딕", 9),
                Location  = new Point(10, 14)
            };

            btnAdd.Location    = new Point(520, 8);
            btnAdd.Width       = 100;
            btnDelete.Location = new Point(630, 8);
            btnDelete.Width    = 100;

            btnAdd.Click    += BtnAdd_Click;
            btnDelete.Click += BtnDelete_Click;

            pnlBottom.Controls.AddRange(new Control[] { lblCount, btnAdd, btnDelete });

            this.Controls.AddRange(new Control[] { dgv, pnlTop, pnlBottom });
        }

        // ─── 데이터 로드 ────────────────────────────────────────────────────

        private void LoadAll()
        {
            txtSearch.Clear();
            BindGrid(repo.GetAll());
        }

        private void BtnSearch_Click(object? sender, EventArgs e)
        {
            var keyword = txtSearch.Text.Trim();
            if (string.IsNullOrEmpty(keyword)) { LoadAll(); return; }
            BindGrid(repo.SearchByName(keyword));
        }

        private void BindGrid(List<Models.User> users)
        {
            var source = users.Select(u => new
            {
                번호   = u.UserId,
                이름   = u.Name,
                전화번호 = u.Phone,
                이메일 = u.Email
            }).ToList();

            dgv.DataSource = source;
            lblCount.Text  = $"총 {source.Count}명";
        }

        // ─── 추가 ──────────────────────────────────────────────────────────

        private void BtnAdd_Click(object? sender, EventArgs e)
        {
            using var dlg = new UserAddForm();
            if (dlg.ShowDialog(this) != DialogResult.OK || dlg.NewUser == null) return;

            if (repo.Add(dlg.NewUser))
            {
                MessageBox.Show("회원이 추가되었습니다.", "완료",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                LoadAll();
            }
            else
            {
                MessageBox.Show("회원 추가에 실패했습니다.", "오류",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ─── 삭제 ──────────────────────────────────────────────────────────

        private void BtnDelete_Click(object? sender, EventArgs e)
        {
            if (dgv.CurrentRow == null) return;

            int userId = (int)dgv.CurrentRow.Cells["번호"].Value;
            string name = dgv.CurrentRow.Cells["이름"].Value?.ToString() ?? "";

            if (MessageBox.Show($"'{name}' 회원을 삭제하시겠습니까?", "삭제 확인",
                    MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
                return;

            bool success = repo.Delete(userId);
            if (success)
            {
                MessageBox.Show("삭제되었습니다.", "완료",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                LoadAll();
            }
            else
            {
                MessageBox.Show(
                    "삭제할 수 없습니다.\n현재 도서를 대출 중인 회원은 삭제할 수 없습니다.",
                    "삭제 불가", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            }
        }

        // ─── 헬퍼 ──────────────────────────────────────────────────────────

        private static Button MakeButton(string text, Color back) => new Button
        {
            Text      = text,
            Height    = 30,
            BackColor = back,
            ForeColor = Color.White,
            FlatStyle = FlatStyle.Flat,
            Cursor    = Cursors.Hand,
            Font      = new Font("맑은 고딕", 9)
        };
    }
}
