using System.Drawing;
using System.Windows.Forms;
using LibraryManagement.Models;

namespace LibraryManagement.Forms
{
    /// <summary>도서 추가 다이얼로그</summary>
    public class BookAddForm : Form
    {
        private TextBox txtTitle     = null!;
        private TextBox txtAuthor    = null!;
        private TextBox txtPublisher = null!;
        private TextBox txtIsbn      = null!;
        private Button  btnSave      = null!;
        private Button  btnCancel    = null!;

        public Book? NewBook { get; private set; }

        public BookAddForm()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Text            = "도서 추가";
            this.Size            = new Size(400, 300);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox     = false;
            this.MinimizeBox     = false;
            this.StartPosition   = FormStartPosition.CenterParent;
            this.BackColor       = Color.White;

            var layout = new TableLayoutPanel
            {
                Dock        = DockStyle.Fill,
                ColumnCount = 2,
                RowCount    = 6,
                Padding     = new Padding(15)
            };
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 80));
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

            txtTitle     = new TextBox { Dock = DockStyle.Fill };
            txtAuthor    = new TextBox { Dock = DockStyle.Fill };
            txtPublisher = new TextBox { Dock = DockStyle.Fill };
            txtIsbn      = new TextBox { Dock = DockStyle.Fill };

            // Row 0 – 제목 (필수)
            layout.Controls.Add(MakeLabel("제목 *"), 0, 0);
            layout.Controls.Add(txtTitle, 1, 0);
            // Row 1 – 저자
            layout.Controls.Add(MakeLabel("저자"), 0, 1);
            layout.Controls.Add(txtAuthor, 1, 1);
            // Row 2 – 출판사
            layout.Controls.Add(MakeLabel("출판사"), 0, 2);
            layout.Controls.Add(txtPublisher, 1, 2);
            // Row 3 – ISBN
            layout.Controls.Add(MakeLabel("ISBN"), 0, 3);
            layout.Controls.Add(txtIsbn, 1, 3);

            // Row 4 – 안내 문구
            var lblNote = new Label
            {
                Text      = "* 제목은 필수 입력 항목입니다.",
                ForeColor = Color.Gray,
                AutoSize  = true,
                Dock      = DockStyle.Fill
            };
            layout.SetColumnSpan(lblNote, 2);
            layout.Controls.Add(lblNote, 0, 4);

            // Row 5 – 버튼
            var pnlBtn = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.RightToLeft,
                Dock          = DockStyle.Fill
            };

            btnCancel = new Button
            {
                Text      = "취소",
                Width     = 80,
                Height    = 30,
                BackColor = Color.FromArgb(189, 195, 199)
            };
            btnSave = new Button
            {
                Text      = "저장",
                Width     = 80,
                Height    = 30,
                BackColor = Color.FromArgb(52, 152, 219),
                ForeColor = Color.White,
                FlatStyle = FlatStyle.Flat
            };

            btnCancel.Click += (_, _) => { this.DialogResult = DialogResult.Cancel; Close(); };
            btnSave.Click   += BtnSave_Click;

            pnlBtn.Controls.AddRange(new Control[] { btnCancel, btnSave });
            layout.SetColumnSpan(pnlBtn, 2);
            layout.Controls.Add(pnlBtn, 0, 5);

            this.Controls.Add(layout);
            this.AcceptButton = btnSave;
            this.CancelButton = btnCancel;
        }

        private void BtnSave_Click(object? sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(txtTitle.Text))
            {
                MessageBox.Show("제목을 입력하세요.", "입력 오류",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                txtTitle.Focus();
                return;
            }

            NewBook = new Book
            {
                Title     = txtTitle.Text.Trim(),
                Author    = txtAuthor.Text.Trim(),
                Publisher = txtPublisher.Text.Trim(),
                Isbn      = txtIsbn.Text.Trim()
            };

            this.DialogResult = DialogResult.OK;
            Close();
        }

        private static Label MakeLabel(string text) => new Label
        {
            Text      = text,
            TextAlign = ContentAlignment.MiddleRight,
            Dock      = DockStyle.Fill,
            Font      = new Font("맑은 고딕", 9)
        };
    }
}
