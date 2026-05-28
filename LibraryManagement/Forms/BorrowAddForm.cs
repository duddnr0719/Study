using System.Drawing;
using System.Windows.Forms;
using LibraryManagement.Models;
using LibraryManagement.Repositories;

namespace LibraryManagement.Forms
{
    /// <summary>대출 등록 다이얼로그</summary>
    public class BorrowAddForm : Form
    {
        private ComboBox     cmbBook       = null!;
        private ComboBox     cmbUser       = null!;
        private DateTimePicker dtpBorrow   = null!;
        private Label        lblReturn     = null!;
        private Button       btnOk         = null!;
        private Button       btnCancel     = null!;

        private readonly BookRepository bookRepo = new();
        private readonly UserRepository userRepo = new();

        public Borrow? NewBorrow { get; private set; }

        public BorrowAddForm()
        {
            InitializeComponent();
            LoadData();
        }

        private void InitializeComponent()
        {
            this.Text            = "대출 등록";
            this.Size            = new Size(420, 280);
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
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 90));
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

            cmbBook = new ComboBox
            {
                Dock         = DockStyle.Fill,
                DropDownStyle = ComboBoxStyle.DropDownList
            };

            cmbUser = new ComboBox
            {
                Dock         = DockStyle.Fill,
                DropDownStyle = ComboBoxStyle.DropDownList
            };

            dtpBorrow = new DateTimePicker
            {
                Dock   = DockStyle.Fill,
                Format = DateTimePickerFormat.Short,
                Value  = DateTime.Today
            };
            dtpBorrow.ValueChanged += (_, _) => UpdateReturnLabel();

            lblReturn = new Label
            {
                Dock      = DockStyle.Fill,
                TextAlign = ContentAlignment.MiddleLeft,
                Font      = new Font("맑은 고딕", 9),
                ForeColor = Color.FromArgb(52, 73, 94)
            };

            layout.Controls.Add(MakeLabel("도서 선택"), 0, 0);
            layout.Controls.Add(cmbBook,                1, 0);
            layout.Controls.Add(MakeLabel("회원 선택"), 0, 1);
            layout.Controls.Add(cmbUser,                1, 1);
            layout.Controls.Add(MakeLabel("대출일"),    0, 2);
            layout.Controls.Add(dtpBorrow,              1, 2);
            layout.Controls.Add(MakeLabel("반납예정일"),0, 3);
            layout.Controls.Add(lblReturn,              1, 3);

            var lblNote = new Label
            {
                Text      = "반납예정일은 대출일로부터 14일 후입니다.",
                ForeColor = Color.Gray,
                AutoSize  = true,
                Font      = new Font("맑은 고딕", 8)
            };
            layout.SetColumnSpan(lblNote, 2);
            layout.Controls.Add(lblNote, 0, 4);

            var pnlBtn = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.RightToLeft,
                Dock          = DockStyle.Fill
            };

            btnCancel = new Button { Text = "취소", Width = 80, Height = 30,
                BackColor = Color.FromArgb(189, 195, 199) };
            btnOk     = new Button { Text = "대출",  Width = 80, Height = 30,
                BackColor = Color.FromArgb(155, 89, 182),
                ForeColor = Color.White, FlatStyle = FlatStyle.Flat };

            btnCancel.Click += (_, _) => { DialogResult = DialogResult.Cancel; Close(); };
            btnOk.Click     += BtnOk_Click;

            pnlBtn.Controls.AddRange(new Control[] { btnCancel, btnOk });
            layout.SetColumnSpan(pnlBtn, 2);
            layout.Controls.Add(pnlBtn, 0, 5);

            this.Controls.Add(layout);
            this.AcceptButton = btnOk;
            this.CancelButton = btnCancel;

            UpdateReturnLabel();
        }

        private void LoadData()
        {
            // 대출 가능한 도서 목록
            var books = bookRepo.GetAvailable();
            cmbBook.DataSource    = books;
            cmbBook.DisplayMember = "Title";
            cmbBook.ValueMember   = "BookId";

            // 전체 회원 목록
            var users = userRepo.GetAll();
            cmbUser.DataSource    = users;
            cmbUser.DisplayMember = "Name";
            cmbUser.ValueMember   = "UserId";
        }

        private void UpdateReturnLabel()
        {
            lblReturn.Text = dtpBorrow.Value.AddDays(14).ToString("yyyy-MM-dd");
        }

        private void BtnOk_Click(object? sender, EventArgs e)
        {
            if (cmbBook.SelectedItem == null)
            {
                MessageBox.Show("대출할 도서를 선택하세요.", "선택 오류",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }
            if (cmbUser.SelectedItem == null)
            {
                MessageBox.Show("회원을 선택하세요.", "선택 오류",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                return;
            }

            var book = (Book)cmbBook.SelectedItem;
            var user = (User)cmbUser.SelectedItem;

            NewBorrow = new Borrow
            {
                BookId     = book.BookId,
                UserId     = user.UserId,
                BorrowDate = dtpBorrow.Value.Date,
                ReturnDate = dtpBorrow.Value.Date.AddDays(14)
            };

            DialogResult = DialogResult.OK;
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
