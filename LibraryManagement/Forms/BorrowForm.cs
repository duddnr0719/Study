using System.Drawing;
using System.Windows.Forms;
using LibraryManagement.Repositories;

namespace LibraryManagement.Forms
{
    /// <summary>대출/반납 관리 폼 — borrow 테이블 조회/대출/반납</summary>
    public class BorrowForm : Form
    {
        private DataGridView dgv        = null!;
        private RadioButton  rbAll      = null!;
        private RadioButton  rbActive   = null!;
        private RadioButton  rbReturned = null!;
        private Button       btnBorrow  = null!;
        private Button       btnReturn  = null!;
        private Label        lblCount   = null!;

        private readonly BorrowRepository repo = new();

        public BorrowForm()
        {
            InitializeComponent();
            LoadAll();
        }

        private void InitializeComponent()
        {
            this.Text          = "대출 / 반납 관리";
            this.Size          = new Size(900, 560);
            this.StartPosition = FormStartPosition.CenterParent;
            this.BackColor     = Color.White;

            // ── 필터 패널 ─────────────────────────────────────────────────
            var pnlTop = new Panel
            {
                Dock      = DockStyle.Top,
                Height    = 50,
                BackColor = Color.FromArgb(236, 240, 241),
                Padding   = new Padding(10, 10, 10, 8)
            };

            var lblFilter = new Label
            {
                Text     = "필터:",
                Location = new Point(10, 14),
                AutoSize = true,
                Font     = new Font("맑은 고딕", 9)
            };

            rbAll      = MakeRadio("전체",    new Point(55,  13));
            rbActive   = MakeRadio("대출중",  new Point(120, 13));
            rbReturned = MakeRadio("반납완료", new Point(185, 13));
            rbAll.Checked = true;

            rbAll.CheckedChanged      += (_, _) => { if (rbAll.Checked)      LoadAll();      };
            rbActive.CheckedChanged   += (_, _) => { if (rbActive.Checked)   LoadActive();   };
            rbReturned.CheckedChanged += (_, _) => { if (rbReturned.Checked) LoadReturned(); };

            pnlTop.Controls.AddRange(new Control[]
                { lblFilter, rbAll, rbActive, rbReturned });

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
            dgv.CellFormatting += Dgv_CellFormatting;

            // ── 하단 버튼 패널 ────────────────────────────────────────────
            var pnlBottom = new Panel
            {
                Dock      = DockStyle.Bottom,
                Height    = 50,
                BackColor = Color.FromArgb(236, 240, 241),
                Padding   = new Padding(10, 8, 10, 8)
            };

            btnBorrow = MakeButton("📖 대출 등록", Color.FromArgb(155, 89, 182));
            btnReturn = MakeButton("✅ 반납 처리", Color.FromArgb(39, 174, 96));
            lblCount  = new Label
            {
                AutoSize  = true,
                ForeColor = Color.FromArgb(52, 73, 94),
                Font      = new Font("맑은 고딕", 9),
                Location  = new Point(10, 14)
            };

            btnBorrow.Location = new Point(680, 8);
            btnBorrow.Width    = 100;
            btnReturn.Location = new Point(790, 8);
            btnReturn.Width    = 100;

            btnBorrow.Click += BtnBorrow_Click;
            btnReturn.Click += BtnReturn_Click;

            pnlBottom.Controls.AddRange(new Control[] { lblCount, btnBorrow, btnReturn });

            this.Controls.AddRange(new Control[] { dgv, pnlTop, pnlBottom });
        }

        // ─── 데이터 로드 ────────────────────────────────────────────────────

        private void LoadAll()      => BindGrid(repo.GetAll());
        private void LoadActive()   => BindGrid(repo.GetActive());
        private void LoadReturned() => BindGrid(
            repo.GetAll().Where(b => b.IsReturned).ToList());

        private void BindGrid(List<Models.Borrow> borrows)
        {
            var source = borrows.Select(b => new
            {
                대출번호   = b.BorrowId,
                도서명    = b.BookTitle,
                회원명    = b.UserName,
                대출일    = b.BorrowDate.ToString("yyyy-MM-dd"),
                반납예정일 = b.ReturnDateText,
                상태      = b.StatusText
            }).ToList();

            dgv.DataSource = source;
            lblCount.Text  = $"총 {source.Count}건";
        }

        // ─── 셀 색상 — 상태에 따라 표시 ─────────────────────────────────

        private void Dgv_CellFormatting(object? sender, DataGridViewCellFormattingEventArgs e)
        {
            if (dgv.Columns[e.ColumnIndex]?.Name == "상태" && e.Value != null
                && e.CellStyle != null)
            {
                e.CellStyle.ForeColor = e.Value?.ToString() == "대출중"
                    ? Color.FromArgb(192, 57, 43)
                    : Color.FromArgb(39, 174, 96);
                e.CellStyle.Font = new Font("맑은 고딕", 9, FontStyle.Bold);
                e.CellStyle.Alignment = DataGridViewContentAlignment.MiddleCenter;
            }
        }

        // ─── 대출 등록 ─────────────────────────────────────────────────────

        private void BtnBorrow_Click(object? sender, EventArgs e)
        {
            using var dlg = new BorrowAddForm();
            if (dlg.ShowDialog(this) != DialogResult.OK || dlg.NewBorrow == null) return;

            try
            {
                if (repo.Add(dlg.NewBorrow))
                {
                    MessageBox.Show("대출이 등록되었습니다.", "완료",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    LoadAll();
                    rbAll.Checked = true;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"대출 등록 실패:\n{ex.Message}", "오류",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ─── 반납 처리 ─────────────────────────────────────────────────────

        private void BtnReturn_Click(object? sender, EventArgs e)
        {
            if (dgv.CurrentRow == null) return;

            string status = dgv.CurrentRow.Cells["상태"].Value?.ToString() ?? "";
            if (status == "반납완료")
            {
                MessageBox.Show("이미 반납된 도서입니다.", "알림",
                    MessageBoxButtons.OK, MessageBoxIcon.Information);
                return;
            }

            int    borrowId = (int)dgv.CurrentRow.Cells["대출번호"].Value;
            string bookName = dgv.CurrentRow.Cells["도서명"].Value?.ToString() ?? "";
            string userName = dgv.CurrentRow.Cells["회원명"].Value?.ToString() ?? "";

            if (MessageBox.Show(
                    $"'{userName}' 회원의 '{bookName}' 도서를 반납 처리하시겠습니까?",
                    "반납 확인",
                    MessageBoxButtons.YesNo, MessageBoxIcon.Question) != DialogResult.Yes)
                return;

            try
            {
                if (repo.Return(borrowId))
                {
                    MessageBox.Show("반납이 완료되었습니다.", "완료",
                        MessageBoxButtons.OK, MessageBoxIcon.Information);
                    LoadAll();
                    rbAll.Checked = true;
                }
            }
            catch (Exception ex)
            {
                MessageBox.Show($"반납 처리 실패:\n{ex.Message}", "오류",
                    MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        // ─── 헬퍼 ──────────────────────────────────────────────────────────

        private static RadioButton MakeRadio(string text, Point loc) => new RadioButton
        {
            Text     = text,
            Location = loc,
            AutoSize = true,
            Font     = new Font("맑은 고딕", 9)
        };

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
