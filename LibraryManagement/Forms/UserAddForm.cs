using System.Drawing;
using System.Windows.Forms;
using LibraryManagement.Models;

namespace LibraryManagement.Forms
{
    /// <summary>회원 추가 다이얼로그</summary>
    public class UserAddForm : Form
    {
        private TextBox txtName  = null!;
        private TextBox txtPhone = null!;
        private TextBox txtEmail = null!;
        private Button  btnSave   = null!;
        private Button  btnCancel = null!;

        public User? NewUser { get; private set; }

        public UserAddForm()
        {
            InitializeComponent();
        }

        private void InitializeComponent()
        {
            this.Text            = "회원 추가";
            this.Size            = new Size(380, 240);
            this.FormBorderStyle = FormBorderStyle.FixedDialog;
            this.MaximizeBox     = false;
            this.MinimizeBox     = false;
            this.StartPosition   = FormStartPosition.CenterParent;
            this.BackColor       = Color.White;

            var layout = new TableLayoutPanel
            {
                Dock        = DockStyle.Fill,
                ColumnCount = 2,
                RowCount    = 5,
                Padding     = new Padding(15)
            };
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Absolute, 80));
            layout.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));

            txtName  = new TextBox { Dock = DockStyle.Fill };
            txtPhone = new TextBox { Dock = DockStyle.Fill };
            txtEmail = new TextBox { Dock = DockStyle.Fill };

            layout.Controls.Add(MakeLabel("이름 *"),   0, 0);
            layout.Controls.Add(txtName,               1, 0);
            layout.Controls.Add(MakeLabel("전화번호"), 0, 1);
            layout.Controls.Add(txtPhone,              1, 1);
            layout.Controls.Add(MakeLabel("이메일"),   0, 2);
            layout.Controls.Add(txtEmail,              1, 2);

            var lblNote = new Label
            {
                Text      = "* 이름은 필수 입력 항목입니다.",
                ForeColor = Color.Gray,
                AutoSize  = true,
                Dock      = DockStyle.Fill
            };
            layout.SetColumnSpan(lblNote, 2);
            layout.Controls.Add(lblNote, 0, 3);

            var pnlBtn = new FlowLayoutPanel
            {
                FlowDirection = FlowDirection.RightToLeft,
                Dock          = DockStyle.Fill
            };

            btnCancel = new Button { Text = "취소", Width = 80, Height = 30,
                BackColor = Color.FromArgb(189, 195, 199) };
            btnSave   = new Button { Text = "저장", Width = 80, Height = 30,
                BackColor = Color.FromArgb(46, 204, 113),
                ForeColor = Color.White, FlatStyle = FlatStyle.Flat };

            btnCancel.Click += (_, _) => { DialogResult = DialogResult.Cancel; Close(); };
            btnSave.Click   += BtnSave_Click;

            pnlBtn.Controls.AddRange(new Control[] { btnCancel, btnSave });
            layout.SetColumnSpan(pnlBtn, 2);
            layout.Controls.Add(pnlBtn, 0, 4);

            this.Controls.Add(layout);
            this.AcceptButton = btnSave;
            this.CancelButton = btnCancel;
        }

        private void BtnSave_Click(object? sender, EventArgs e)
        {
            if (string.IsNullOrWhiteSpace(txtName.Text))
            {
                MessageBox.Show("이름을 입력하세요.", "입력 오류",
                    MessageBoxButtons.OK, MessageBoxIcon.Warning);
                txtName.Focus();
                return;
            }

            NewUser = new User
            {
                Name  = txtName.Text.Trim(),
                Phone = txtPhone.Text.Trim(),
                Email = txtEmail.Text.Trim()
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
